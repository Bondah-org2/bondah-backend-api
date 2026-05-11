import django_filters
from . models import DocumentVerification


class BondmakerFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method="filter_status")

    class Meta:
        model = DocumentVerification
        fields = ["status"]

    def filter_status(self, queryset, name, value):
        if value == "all":
            return queryset
        return queryset.filter(status=value)
