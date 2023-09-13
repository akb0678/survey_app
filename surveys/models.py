from django.db import models

class Survey(models.Model):
    title = models.CharField(max_length=255)

class Question(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    text = models.CharField(max_length=255)

class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    user_id = models.IntegerField()  # You can change this to link to a User model
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField()  # Assuming options are integers from 1 to 10
