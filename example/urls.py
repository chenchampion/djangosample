"""example URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url, include
#from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from django.contrib import admin
from retail.views import *
from core.models import CustomUser as User
from oscar.app import application
from oscar.apps.company.views import CompanyViewSet

from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token, refresh_jwt_token
# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="users-detail", lookup_field='pk')
    #companys = serializers.HyperlinkedIdentityField(view_name="company", lookup_field='companys')
    class Meta:
        model = User
        fields = ('pk', 'username', 'password', 'email', 'url' )
        write_only_fields = ('password',)
        read_only_fields = ('pk',)

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    #queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        companys = user.companys.all()
        if(companys):
            return User.objects.filter(companys__in=companys)
        return User.objects.all()

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(prefix='users', viewset=UserViewSet, base_name='users')
router.register(prefix='chains', viewset=ChainViewSet)
router.register(prefix='stores', viewset=StoreViewSet)
router.register(prefix='employees', viewset=EmployeeViewSet)
router.register(prefix='company', viewset=CompanyViewSet, base_name='company')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^users/(?P<pk>\d+)/$)', User.as_view(), name='customuser-detail'),
    #url(r'^api-token-auth/', obtain_jwt_token),
    #url(r'^api-token-refresh/', refresh_jwt_token),
    #url(r'^api-token-verify/', verify_jwt_token),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^shop/', application.urls),
]
