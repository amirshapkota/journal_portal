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
    city = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    types = serializers.ListField(child=serializers.CharField(), required=False)
    external_ids = serializers.DictField(required=False)
    acronyms = serializers.ListField(child=serializers.CharField(), required=False)
    links = serializers.ListField(child=serializers.CharField(), required=False)
    established = serializers.CharField(required=False)
    status = serializers.CharField(required=False)

    @staticmethod
    def from_ror_result(result):
        # Name: Prefer ror_display/label, fallback to first name
        names = result.get('names', [])
        name = None
        for n in names:
            if 'ror_display' in n.get('types', []) or 'label' in n.get('types', []):
                name = n.get('value')
                break
        if not name and names:
            name = names[0].get('value')
        # Acronyms: All names with type 'acronym'
        acronyms = [n['value'] for n in names if 'acronym' in n.get('types', [])]
        # Links: All link values
        links = [l['value'] for l in result.get('links', []) if 'value' in l]
        # Types
        types = result.get('types', [])
        # External IDs
        ext_ids = {}
        for eid in result.get('external_ids', []):
            t = eid.get('type')
            val = eid.get('preferred') or (eid.get('all') or [None])[0]
            if t and val:
                ext_ids[t] = val
        # Locations
        locations = result.get('locations', [])
        country = country_code = city = location = None
        if locations:
            geo = locations[0].get('geonames_details', {})
            country = geo.get('country_name')
            country_code = geo.get('country_code')
            city = geo.get('name')
            location = ', '.join([v for v in [city, country] if v]) if city or country else None
        # Established
        established = str(result.get('established')) if result.get('established') is not None else None
        # Status
        status = result.get('status')
        return {
            'id': result.get('id'),
            'name': name,
            'country': country,
            'country_code': country_code,
            'city': city,
            'location': location,
            'types': types,
            'external_ids': ext_ids,
            'acronyms': acronyms,
            'links': links,
            'established': established,
            'status': status,
        }
