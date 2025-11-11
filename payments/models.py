from django.db import models

# Create your models here.


class Payment(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="payments")
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name="purchases")
    payment_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=[("Completed", "Completed"), ("Pending", "Pending")],
                              default="Pending")
    payment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"{self.user.email} - {self.course.title} - {self.status}"
