"""Serializers for integrations app (ORCID, OJS, etc.).
Currently minimal as ORCID endpoints are procedural; expand as needed.
"""

from rest_framework import serializers


class ORCIDStatusSerializer(serializers.Serializer):
    connected = serializers.BooleanField()
    status = serializers.CharField()
    orcid_id = serializers.CharField(allow_null=True, required=False)
    token_scope = serializers.CharField(allow_blank=True, required=False)
    expires_at = serializers.CharField(allow_null=True, required=False)
    last_sync_at = serializers.CharField(allow_null=True, required=False)


class ROROrganizationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    country = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    types = serializers.ListField(child=serializers.CharField(), required=False)
    external_ids = serializers.DictField(required=False)
    acronyms = serializers.ListField(child=serializers.CharField(), required=False)
    addresses = serializers.ListField(child=serializers.DictField(), required=False)
    links = serializers.ListField(child=serializers.CharField(), required=False)
    established = serializers.CharField(required=False)
    status = serializers.CharField(required=False)

    @staticmethod
    def from_ror_result(result):
        # Map ROR API result to serializer fields
        # ROR API: name is at result['name'], country at result['country']['country_name'],
        # location is first address's city/country if available
        addresses = result.get('addresses', [])
        location = None
        if addresses:
            city = addresses[0].get('city')
            country = addresses[0].get('country')
            location = ', '.join([v for v in [city, country] if v])
        country_name = None
        country_code = None
        if addresses:
            country_name = addresses[0].get('country')
            country_code = addresses[0].get('country_code')
        return {
            'id': result.get('id'),
            'name': result.get('name'),
            'country': country_name,
            'country_code': country_code,
            'location': location,
            'types': result.get('types', []),
            'external_ids': result.get('external_ids', {}),
            'acronyms': result.get('acronyms', []),
            'addresses': addresses,
            'links': result.get('links', []),
            'established': result.get('established'),
            'status': result.get('status'),
        }
