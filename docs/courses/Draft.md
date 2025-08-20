now we wanna design the courses app, in this app we have the courses models that will buy by users, in the courses we have different things for teaching and learning, i will put the overview of this models that delivered to me: (this models are just a quick draft to preview the logic)
# Courses

```python
class Course(models.Model):
    name
    description
    banner_image
    index_image

class Package(models.Model):
 name
 description
 banner_image
 index_image

class Assignment(models.Model):  # ~ Homework Assigned to students
 title
 description
 deadline: Datetime

class AssignmentFile(models.Model):
 title (null=True, blank=True)
 file: File 

class HomeWork(models.Model):
 student
 description
 assignment

class HomeWorkFile(models.Model):
 title (null=True, blank=True)
 file: File
 homework

class Booklet(models.Model):
 title
 description

class BookletPage(models.Model):
 title
 description
 content  # Hypertext
 files  # multiple files related to a page

class BookletFile(models.Model):
 title  # null=True, blank=True
 description  # null=True, blank=True
 file

class Forum(models.Model):
 title
 description  # null=True, blank=True

class ForumTopic(models.Model):
 title
 description  # Required

class ForumPost(models.Model):
 topic
 replied_post  # null=True, blank=True
 content  # Required

class Exam(models.Model):
 title
 description
 duration

class ExamQuestionFile(models.Model):
 title  # null=True, blank=True
 file

class ExamQuestion(models.Model):
 question_type  # multi choice, textarea (?), custom
 title
 description
 file  # Relation to ExamQuestionFile

class ExamConduction(models.Model):
 exam
 start_datetime
 end_datetime
 Correctors # Relation to Teachers/Proffesors

```

do not bias your self with any of provided codes above
in this phase we will focuse on exams, the exams is define by admins and edited by teachers and each question have its own properties and there is no limitation by the exam into questions but questions inherit some of the exam properties like the "default correct/false score" and etc...
for example a question can be in format of four-choice quize or have a file (for now the questions can only contain image files) as the question description (but the question object as it self can also contain the description and etc...) and also the question answer can configure to be a file (so the user should upload their answers as a file and for now only images are acceptable but we should implement the pdf also now), also a question with text area for answering can answered by uploading the file (the both ways are allowed if its configured)
each users that purchased the course can query their active exams in their dashboard and exams have a start date-time and a duration (that defined how long the user is allowed to answer all the exam from the time they started the exam)
we should implement the auto-saving feature and save an cached like from the last modified answers but do not submit them until the user submit it and if the exam duration is ended the last saved answers will automatically submit
exams have a default value of total score and minimum score of acception and the exam result after correction by teachers (or auto correcting if all the exam is in choices mode) is calculate by it, also we can configure the exam to do not show the result score of exam to users if they are accepted (an user can accept an exam even if they are not achive the minimum score)
also the auto-correctable exams can configure to do not publish the final result of users's exams if its deefine
the exams can import into many courses as wanted and if an user is present in both exams should participate the exam again unless its define to use the last user's related exam result and apply it in new course
the related teachers to each course is authorized to correct the exams but also exams can assign to foreign techers to bbe corrected if its defined in the exam properties
for now all the courses are free and users can join them as if they wanted but the courses can be not "public" and have "purchase" mode (we will implement the purchase workfllow but we should have this option now but can be implemented later)