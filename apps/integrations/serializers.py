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


class OpenAlexAuthorSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    orcid = serializers.CharField(allow_null=True, required=False)
    works_count = serializers.IntegerField(required=False)
    cited_by_count = serializers.IntegerField(required=False)
    last_known_institutions = serializers.ListField(child=serializers.CharField(), required=False)
    # Add more fields as needed

    @staticmethod
    def from_openalex_result(result):
        # last_known_institutions is a list of dicts; extract display_names
        institutions = result.get('last_known_institutions') or []
        inst_names = [i.get('display_name') for i in institutions if i.get('display_name')]
        return {
            'id': result.get('id'),
            'display_name': result.get('display_name'),
            'orcid': result.get('orcid'),
            'works_count': result.get('works_count'),
            'cited_by_count': result.get('cited_by_count'),
            'last_known_institutions': inst_names,
        }


class OpenAlexInstitutionSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    ror = serializers.CharField(allow_null=True, required=False)
    country_code = serializers.CharField(allow_null=True, required=False)
    type = serializers.CharField(allow_null=True, required=False)
    # Add more fields as needed

    @staticmethod
    def from_openalex_result(result):
        return {
            'id': result.get('id'),
            'display_name': result.get('display_name'),
            'ror': result.get('ror'),
            'country_code': result.get('country_code'),
            'type': result.get('type'),
        }


class OpenAlexWorkSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    publication_year = serializers.IntegerField(required=False)
    doi = serializers.CharField(allow_null=True, required=False)
    type = serializers.CharField(allow_null=True, required=False)
    authorships = serializers.ListField(child=serializers.DictField(), required=False)
    # Add more fields as needed

    @staticmethod
    def from_openalex_result(result):
        return {
            'id': result.get('id'),
            'display_name': result.get('display_name'),
            'publication_year': result.get('publication_year'),
            'doi': result.get('doi'),
            'type': result.get('type'),
            'authorships': result.get('authorships', []),
        }
    
class DOAJJournalSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    publisher = serializers.CharField(allow_null=True, required=False)
    issn = serializers.ListField(child=serializers.CharField(), required=False)
    country = serializers.CharField(allow_null=True, required=False)
    subjects = serializers.ListField(child=serializers.CharField(), required=False)
    # Add more fields as needed

    @staticmethod
    def from_doaj_result(result):
        bibjson = result.get('bibjson', {})
        # ISSN: try bibjson['issn'], then bibjson['identifier'] (type: 'issn')
        issn_list = []
        issn_raw = bibjson.get('issn', [])
        for i in issn_raw:
            if isinstance(i, str):
                issn_list.append(i)
            elif isinstance(i, dict) and 'value' in i:
                issn_list.append(i['value'])
        # If still empty, try bibjson['identifier']
        if not issn_list:
            for ident in bibjson.get('identifier', []):
                if ident.get('type') == 'issn' and ident.get('id'):
                    issn_list.append(ident['id'])
        # Country: try bibjson['country'], then publisher['country']
        country = bibjson.get('country')
        publisher = bibjson.get('publisher')
        if not country and isinstance(publisher, dict):
            country = publisher.get('country')
        return {
            'id': result.get('id'),
            'title': bibjson.get('title'),
            'publisher': publisher,
            'issn': issn_list,
            'country': country,
            'subjects': [s.get('term') for s in bibjson.get('subject', []) if s.get('term')],
        }


class DOAJArticleSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    doi = serializers.CharField(allow_null=True, required=False)
    journal = serializers.CharField(allow_null=True, required=False)
    year = serializers.CharField(allow_null=True, required=False)
    authors = serializers.ListField(child=serializers.CharField(), required=False)
    # Add more fields as needed

    @staticmethod
    def from_doaj_result(result):
        bibjson = result.get('bibjson', {})
        return {
            'id': result.get('id'),
            'title': bibjson.get('title'),
            'doi': bibjson.get('identifier', [{}])[0].get('id') if bibjson.get('identifier') else None,
            'journal': bibjson.get('journal', {}).get('title') if bibjson.get('journal') else None,
            'year': bibjson.get('year'),
            'authors': [a.get('name') for a in bibjson.get('author', []) if a.get('name')],
        }


class DOAJInclusionCheckSerializer(serializers.Serializer):
    issn = serializers.CharField()
    included = serializers.BooleanField()


class DOAJSubmitUpdateSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField(allow_blank=True, required=False)

# --- OJS Review Serializer ---
class OJSReviewSerializer(serializers.Serializer):
    id = serializers.CharField()
    submission_id = serializers.CharField()
    reviewer_id = serializers.CharField()
    recommendation = serializers.CharField(allow_blank=True, required=False)
    comments = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField()
    # Add more fields as needed

    @staticmethod
    def from_ojs_result(result):
        return {
            'id': result.get('id'),
            'submission_id': result.get('submission_id'),
            'reviewer_id': result.get('reviewer_id'),
            'recommendation': result.get('recommendation', ''),
            'comments': result.get('comments', ''),
            'status': result.get('status'),
        }

# --- OJS Comment Serializer ---
class OJSCommentSerializer(serializers.Serializer):
    id = serializers.CharField()
    submission_id = serializers.CharField()
    user_id = serializers.CharField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField(required=False)
    # Add more fields as needed

    @staticmethod
    def from_ojs_result(result):
        return {
            'id': result.get('id'),
            'submission_id': result.get('submission_id'),
            'user_id': result.get('user_id'),
            'content': result.get('content'),
            'created_at': result.get('created_at'),
        }
# --- OJS User Serializer ---
class OJSUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    roles = serializers.ListField(child=serializers.CharField(), required=False)
    # Add more fields as needed

    @staticmethod
    def from_ojs_result(result):
        return {
            'id': result.get('id'),
            'email': result.get('email'),
            'first_name': result.get('first_name', ''),
            'last_name': result.get('last_name', ''),
            'roles': result.get('roles', []),
        }
# --- OJS Article Serializer ---
class OJSArticleSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    abstract = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField()
    # Add more fields as needed (authors, files, etc.)

    @staticmethod
    def from_ojs_result(result):
        return {
            'id': result.get('id'),
            'title': result.get('title'),
            'abstract': result.get('abstract', ''),
            'status': result.get('status'),
        }

# --- OJS Serializers ---
class OJSJournalSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    # Add more fields as needed

    @staticmethod
    def from_ojs_result(result):
        return {
            'id': result.get('id'),
            'name': result.get('name'),
            'description': result.get('description', ''),
        }


class OJSSubmissionSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    # Add more fields as needed

    @staticmethod
    def from_ojs_result(result):
        return {
            'id': result.get('id'),
            'title': result.get('title'),
            'status': result.get('status'),
        }

# Sentry serializers
class SentryIssueSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    culprit = serializers.CharField(allow_blank=True, required=False)
    permalink = serializers.CharField(allow_blank=True, required=False)
    short_id = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField(allow_blank=True, required=False)
    level = serializers.CharField(allow_blank=True, required=False)
    count = serializers.IntegerField(required=False)
    user_count = serializers.IntegerField(required=False)
    first_seen = serializers.DateTimeField(required=False)
    last_seen = serializers.DateTimeField(required=False)
    project = serializers.DictField(required=False)
    metadata = serializers.DictField(required=False)

    @staticmethod
    def from_sentry_result(result):
        return {
            'id': result.get('id'),
            'title': result.get('title') or result.get('metadata', {}).get('title', ''),
            'culprit': result.get('culprit', ''),
            'permalink': result.get('permalink', ''),
            'short_id': result.get('shortId', ''),
            'status': result.get('status', ''),
            'level': result.get('level', ''),
            'count': result.get('count', 0),
            'user_count': result.get('userCount', 0),
            'first_seen': result.get('firstSeen'),
            'last_seen': result.get('lastSeen'),
            'project': result.get('project', {}),
            'metadata': result.get('metadata', {}),
        }


class SentryEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    event_id = serializers.CharField()
    message = serializers.CharField(allow_blank=True, required=False)
    title = serializers.CharField(allow_blank=True, required=False)
    platform = serializers.CharField(allow_blank=True, required=False)
    datetime = serializers.DateTimeField(required=False)
    tags = serializers.ListField(child=serializers.DictField(), required=False)
    context = serializers.DictField(required=False)
    entries = serializers.ListField(child=serializers.DictField(), required=False)

    @staticmethod
    def from_sentry_result(result):
        return {
            'id': result.get('id'),
            'event_id': result.get('eventID') or result.get('id'),
            'message': result.get('message', ''),
            'title': result.get('title', ''),
            'platform': result.get('platform', ''),
            'datetime': result.get('dateCreated') or result.get('dateReceived'),
            'tags': result.get('tags', []),
            'context': result.get('context', {}),
            'entries': result.get('entries', []),
        }


class SentryProjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField()
    name = serializers.CharField()
    platform = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField(allow_blank=True, required=False)
    date_created = serializers.DateTimeField(required=False)

    @staticmethod
    def from_sentry_result(result):
        return {
            'id': result.get('id'),
            'slug': result.get('slug'),
            'name': result.get('name'),
            'platform': result.get('platform', ''),
            'status': result.get('status', ''),
            'date_created': result.get('dateCreated'),
        }


class SentryStatsSerializer(serializers.Serializer):
    stats = serializers.ListField(child=serializers.ListField(), required=False)
    start = serializers.IntegerField(required=False)
    end = serializers.IntegerField(required=False)

    @staticmethod
    def from_sentry_result(result):
        return {
            'stats': result if isinstance(result, list) else [],
            'start': result[0][0] if isinstance(result, list) and len(result) > 0 else None,
            'end': result[-1][0] if isinstance(result, list) and len(result) > 0 else None,
        }
