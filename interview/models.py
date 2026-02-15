from django.db import models
from django.contrib.auth.models import User

class InterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resume_text = models.TextField(null=True, blank=True)
    current_question_number = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    domain = models.CharField(max_length=100, default="General")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} - {self.user.username}"
    
class InterviewResponse(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    ai_score = models.IntegerField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.session.current_question_number} - Session {self.session.id}"   

class Resume(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pdf = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username