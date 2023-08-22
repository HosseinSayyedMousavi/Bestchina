from django.db import models
from solo.models import SingletonModel
import json

STATUS_CHOICES = [('stopped', 'stopped'),('running', 'running'),('Finished', 'Finished')]
class CreateImporter(SingletonModel):
    category = models.OneToOneField("Category",max_length=255,null=True,unique=True,on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=STATUS_CHOICES,max_length=255,default='running')
    is_periodic = models.BooleanField(default=False)
    period_per_day = models.PositiveIntegerField(default = 10)
    def save(self, **kwargs):
        try:
            Importer.objects.create(
            category=self.category,
            status=self.status,
            is_periodic=self.is_periodic,
            period_per_day=self.period_per_day)
        except Exception as e:
            if not self.pk: 
                pass
            else:
                raise e
        super(CreateImporter, self).save(**kwargs)


class Importer(models.Model):
    category = models.OneToOneField("Category",max_length=255,null=False,unique=True,on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=STATUS_CHOICES,max_length=255,default='running')
    is_periodic = models.BooleanField(default=False)
    period_per_day = models.PositiveIntegerField(default = 10)
    Progress_percentage = models.PositiveIntegerField(default = 0)



           

class Category(models.Model):
    Code = models.CharField(max_length=255,null=False,unique=True)
    Name = models.CharField(max_length=255,null=False)
    FarsiName = models.CharField(max_length=255,null=False)
    ParentCode = models.CharField(max_length=255,null=False)
    Status = models.CharField(max_length=255,null=False)
    def __str__(self):
        return self.Name
    
    class Meta:
        verbose_name="Category"
        verbose_name_plural="Categories"