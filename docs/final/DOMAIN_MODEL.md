# Domain Model

MentorHub centers on the `User` aggregate and supporting profile entities. Phone numbers are the primary identifier; additional profile data unlocks catalog access.

## Entities

### User
- `id` (UUID)
- `phone` (E.164, immutable)
- `display_name` (required at first verify)
- `email` (optional, unique)
- `roles` (`student`, `teacher`, `mentor`, `staff_admin`, `superadmin`)
- `is_profile_complete`, timestamps

### AuthArtifacts
- **OTPCode**: `phone`, `code_hash`, `expires_at`, `used_at`
- **RefreshSession**: `jti`, `user_id`, `issued_at`, `expires_at`, `rotated_from`, `revoked_at`, `ip`, `user_agent`

### Profile Sub-aggregates
- **IdentityInfo**: encrypted `national_id`, `date_of_birth`, verification status
- **EducationalProfile**: `level`, `grade`, optional `study_branch`, up to 3 `olympiads`
- **Location**: `province`, `city`
- **ParentContact**: phone + OTP verification for minors

### Taxonomies
- **EducationalLevel**, **StudyBranch**, **Olympiad**, **Location** entries maintained by admins.

## Relationships
```
User (1) ── (1) IdentityInfo
   │
   ├─ (0..1) EducationalProfile ── (0..*) Olympiad
   │
   ├─ (1) Location
   │
   └─ (0..1) ParentContact [required if minor]

User (1) ── (M) RefreshSession
Phone ────── (M) OTPCode
```

## Business Rules

- `display_name` must be set before non-guest actions.
- Minor determination: `today - date_of_birth < AGE_THRESHOLD` ⇒ ParentContact required.
- `study_branch` required only when `level.is_high_school` is true.
- Max three unique olympiads per user; `olympiad_degree` fixed per olympiad.

## Validation Matrix

| Entity | Rule |
| --- | --- |
| User | `display_name` required at first verify; `email` unique |
| OTPCode | 6 digits; 5 minute TTL; per-phone and per-IP throttles |
| IdentityInfo | ≤5 submissions/24h; external API timeout & retry |
| EducationalProfile | grade within level range; branch required for high school; ≤3 unique olympiads |
| ParentContact | Required & verified for minors only |

For operational policies see [RUNBOOKS](RUNBOOKS.md).
