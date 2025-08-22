from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import City, EducationalLevel, Olympiad, Province, StudyBranch, SchoolType
from .serializers import (
    CitySerializer,
    EducationalLevelSerializer,
    OlympiadSerializer,
    ProvinceListSerializer,
    StudyBranchSerializer,
    SchoolTypeSerializer,
)


@extend_schema(tags=["Taxonomy"])
class EducationalLevelListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: EducationalLevelSerializer(many=True)},
    )
    def get(self, request):
        qs = EducationalLevel.objects.all()
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        ordering = request.query_params.get("ordering") or "name"
        if ordering.lstrip("-") != "name":
            ordering = "name"
        qs = qs.order_by(ordering)
        serializer = EducationalLevelSerializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Taxonomy"])
class StudyBranchListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("level", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("active", bool, OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: StudyBranchSerializer(many=True),
            400: OpenApiResponse(description="level is required"),
            404: OpenApiResponse(description="level not found"),
        },
    )
    def get(self, request):
        level_id = request.query_params.get("level")
        if not level_id:
            return Response(
                {"error": {"code": "level_required", "message": "level is required"}},
                status=400,
            )
        try:
            level = EducationalLevel.objects.get(id=level_id, is_high_school=True)
        except EducationalLevel.DoesNotExist:
            return Response(
                {"error": {"code": "level_not_found", "message": "level not found"}},
                status=404,
            )
        branches = StudyBranch.objects.filter(level=level)
        if request.query_params.get("active") == "true":
            branches = branches.filter(is_active=True)
        branches = branches.order_by("name")
        serializer = StudyBranchSerializer(branches, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Taxonomy"])
class SchoolTypeListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "published", bool, OpenApiParameter.QUERY, required=False
            ),
        ],
        responses={200: SchoolTypeSerializer(many=True)},
    )
    def get(self, request):
        school_types = SchoolType.objects.all()
        serializer = SchoolTypeSerializer(school_types, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Taxonomy"])
class OlympiadListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "published", bool, OpenApiParameter.QUERY, required=False
            ),
        ],
        responses={200: OlympiadSerializer(many=True)},
    )
    def get(self, request):
        published = request.query_params.get("published")
        qs = Olympiad.objects.all()
        if published is None or published.lower() == "true":
            qs = qs.filter(published=True)
        elif published.lower() == "false":
            qs = qs.filter(published=False)
        qs = qs.order_by("name")
        serializer = OlympiadSerializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Taxonomy"])
class LocationListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("state", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("province", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("all", bool, OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: OpenApiResponse(description="List of provinces or cities"),
        },
    )
    def get(self, request):
        q = request.query_params.get("q")
        state_param = request.query_params.get("state") or request.query_params.get(
            "province"
        )
        all_flag = request.query_params.get("all") == "true"

        if state_param:
            try:
                if state_param.isdigit():
                    province = Province.objects.get(id=int(state_param))
                else:
                    province = Province.objects.get(slug=state_param)
            except Province.DoesNotExist:
                return Response([])
            cities = City.objects.filter(province=province)
            if q:
                cities = cities.filter(name__icontains=q)
            cities = cities.order_by("name")
            return Response(CitySerializer(cities, many=True).data)

        provinces = Province.objects.all()
        if q:
            city_ids = City.objects.filter(name__icontains=q).values_list(
                "province_id", flat=True
            )
            provinces = provinces.filter(Q(name__icontains=q) | Q(id__in=city_ids))
        if all_flag:
            provinces = provinces.order_by("name").prefetch_related("city_set")
            data = []
            for prov in provinces:
                cities = prov.city_set.all()
                if q:
                    cities = [c for c in cities if q.lower() in c.name.lower()]
                    if q.lower() not in prov.name.lower() and not cities:
                        continue
                data.append(
                    {
                        "id": prov.id,
                        "name": prov.name,
                        "slug": prov.slug,
                        "cities": CitySerializer(cities, many=True).data,
                    }
                )
            return Response(data)

        provinces = provinces.annotate(cities_count=Count("city")).order_by("name")
        serializer = ProvinceListSerializer(provinces, many=True)
        return Response(serializer.data)
