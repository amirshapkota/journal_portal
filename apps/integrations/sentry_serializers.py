"""
Sentry API serializers for integrations app.
"""

from rest_framework import serializers


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
