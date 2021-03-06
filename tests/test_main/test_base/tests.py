# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.test import TestCase, TransactionTestCase
from django.db import connection, DatabaseError
from django.db.models import F
from django.db.models.fields.related import ForeignKey

from .models import BigS, FieldsTest, Foo, Bar


class FirebirdTest(TestCase):
    def setUp(self):
        pass

    def test_server_version(self):
        version = connection.server_version
        self.assertNotEqual(version, '')

    def test_firebird_version(self):
        version = connection.ops.firebird_version
        self.assertNotEqual(version, [])


class DatabaseOperationsTest(TestCase):
    def setUp(self):
        self.ops = connection.ops

    def test_get_sequence_name(self):
        sq_name = self.ops.get_sequence_name('TEST')
        self.assertEqual(sq_name, '"TEST_SQ"')

    def test_drop_sequence_sql(self):
        sql = self.ops.drop_sequence_sql('TEST')
        self.assertEqual(sql, 'DROP SEQUENCE "TEST_SQ"')

    def test_date_extract_sql(self):
        sql = self.ops.date_extract_sql('week_day', 'DATE_FIELD')
        value = "EXTRACT(WEEKDAY FROM DATE_FIELD) + 1"
        self.assertEqual(sql, value)

        sql = self.ops.date_extract_sql('year', 'DATE_FIELD')
        value = "EXTRACT(YEAR FROM DATE_FIELD)"
        self.assertEqual(sql, value)

        sql = self.ops.date_extract_sql('month', 'DATE_FIELD')
        value = "EXTRACT(MONTH FROM DATE_FIELD)"
        self.assertEqual(sql, value)

        sql = self.ops.date_extract_sql('day', 'DATE_FIELD')
        value = "EXTRACT(DAY FROM DATE_FIELD)"
        self.assertEqual(sql, value)

    def test_datetime_trunc_sql(self):
        sql, params = self.ops.datetime_trunc_sql('year', 'DATE_FIELD', None)
        value = "CAST(EXTRACT(year FROM DATE_FIELD)||'-01-01 00:00:00' AS TIMESTAMP)"
        self.assertEqual(sql, value)

        sql, params = self.ops.datetime_trunc_sql('month', 'DATE_FIELD', None)
        value = "CAST(EXTRACT(year FROM DATE_FIELD)||'-'||EXTRACT(month FROM DATE_FIELD)||'-01 00:00:00' AS TIMESTAMP)"
        self.assertEqual(sql, value)

        sql, params = self.ops.datetime_trunc_sql('day', 'DATE_FIELD', None)
        value = "CAST(EXTRACT(year FROM DATE_FIELD)||'-'||EXTRACT(month FROM DATE_FIELD)||'-'||EXTRACT(day FROM DATE_FIELD)||' 00:00:00' AS TIMESTAMP)"
        self.assertEqual(sql, value)

        sql, params = self.ops.datetime_trunc_sql('hour', 'DATE_FIELD', None)
        value = "CAST(EXTRACT(year FROM DATE_FIELD)||'-'||EXTRACT(month FROM DATE_FIELD)||'-'||EXTRACT(day FROM DATE_FIELD)||' '||EXTRACT(hour FROM DATE_FIELD)||':00:00' AS TIMESTAMP)"
        self.assertEqual(sql, value)

        sql, params = self.ops.datetime_trunc_sql('minute', 'DATE_FIELD', None)
        value = "CAST(EXTRACT(year FROM DATE_FIELD)||'-'||EXTRACT(month FROM DATE_FIELD)||'-'||EXTRACT(day FROM DATE_FIELD)||' '||EXTRACT(hour FROM DATE_FIELD)||':'||EXTRACT(minute FROM DATE_FIELD)||':00' AS TIMESTAMP)"
        self.assertEqual(sql, value)

        sql, params = self.ops.datetime_trunc_sql('second', 'DATE_FIELD', None)
        value = "CAST(EXTRACT(year FROM DATE_FIELD)||'-'||EXTRACT(month FROM DATE_FIELD)||'-'||EXTRACT(day FROM DATE_FIELD)||' '||EXTRACT(hour FROM DATE_FIELD)||':'||EXTRACT(minute FROM DATE_FIELD)||':'||EXTRACT(second FROM DATE_FIELD) AS TIMESTAMP)"
        self.assertEqual(sql, value)


class DatabaseSchemaTests(TransactionTestCase):
    def test_no_index_for_foreignkey(self):
        """
        FirebirdSQL already creates indexes automatically for foreign keys. (#70).
        """
        index_sql = connection.schema_editor()._model_indexes_sql(Bar)
        self.assertEqual(index_sql, [])

    def test_fk_index_creation(self):
        new_field = ForeignKey(Foo)
        new_field.set_attributes_from_name(None)
        with connection.schema_editor() as editor:
            editor.add_field(
                Bar,
                new_field
            )
            # Just return indexes others that not automaically created by Fk
            indexes = editor._get_field_indexes(Bar, new_field)
        self.assertEqual(indexes, [])

    def test_fk_remove_issue70(self):
        with connection.schema_editor() as editor:
            editor.remove_field(
                Bar,
                Bar._meta.get_field("a")
            )
        self.assertRaises(DatabaseError)


class SlugFieldTests(TestCase):
    def test_slugfield_max_length(self):
        """
        Make sure SlugField honors max_length (#9706)
        """
        bs = BigS.objects.create(s='slug' * 50)
        bs = BigS.objects.get(pk=bs.pk)
        self.assertEqual(bs.s, 'slug' * 50)


class DateFieldTests(TestCase):
    def tests_date_interval(self):
        obj = FieldsTest()
        obj.pub_date = datetime.now()
        obj.mod_date = obj.pub_date + timedelta(days=3)
        obj.save()

        objs = FieldsTest.objects.filter(mod_date__gte=F('pub_date') + timedelta(days=3)).all()
        self.assertEqual(len(objs), 1)
