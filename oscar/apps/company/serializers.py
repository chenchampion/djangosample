from rest_framework import serializers
from oscar.core.loading import get_model

Company = get_model('company', 'Company')


class CompanySerializer(serializers.ModelSerializer):
    """ Serializer to represent the Company model """
    class Meta:
        model = Company
        fields = ('name', 'code', 'url')
        #read_only_fields = ('code',)

