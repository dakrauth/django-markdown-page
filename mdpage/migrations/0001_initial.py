# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import mdpage.models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarkdownPage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('pub_date', models.DateTimeField(null=True, blank=True)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('status', models.CharField(default='PEND', max_length=4, db_index=True, choices=[('PEND', b'Pending'), ('PUB', b'Published'), ('GONE', b'Withdrawn')])),
                ('slug', models.SlugField(max_length=100)),
                ('title', models.CharField(max_length=100)),
                ('text', models.TextField(blank=True)),
                ('summary', models.TextField(blank=True)),
                ('html', models.TextField(blank=True)),
                ('version', models.IntegerField(default=0)),
                ('locked', models.DateTimeField(null=True, blank=True)),
                ('tags', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
            options={
                'ordering': ('title',),
            },
        ),
        migrations.CreateModel(
            name='MarkdownPageArchive',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.IntegerField()),
                ('created', models.DateTimeField()),
                ('text', models.TextField(blank=True)),
                ('user_id', models.IntegerField(null=True, blank=True)),
                ('page', models.ForeignKey(to='mdpage.MarkdownPage', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('-created',),
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='MarkdownPageType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('pub_date', models.DateTimeField(null=True, blank=True)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('status', models.CharField(default='PEND', max_length=4, db_index=True, choices=[('PEND', b'Pending'), ('PUB', b'Published'), ('GONE', b'Withdrawn')])),
                ('prefix', models.SlugField(unique=True, blank=True)),
                ('description', models.CharField(max_length=100, blank=True)),
                ('show_history', models.BooleanField(default=True)),
                ('show_recent', models.BooleanField(default=True)),
                ('show_text', models.BooleanField(default=True)),
                ('show_topics', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StaticContent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.SlugField(unique=True)),
                ('description', models.CharField(max_length=255, blank=True)),
                ('media', models.FileField(upload_to=mdpage.models.upload_static_content_to)),
                ('type', models.CharField(default=b'application', max_length=20)),
                ('subtype', models.CharField(default=b'octet-stream', max_length=50)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('page', models.ForeignKey(to='mdpage.MarkdownPage', on_delete=models.CASCADE)),
            ],
        ),
        migrations.AddField(
            model_name='markdownpage',
            name='type',
            field=models.ForeignKey(to='mdpage.MarkdownPageType', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='markdownpage',
            unique_together=set([('type', 'slug'), ('type', 'title')]),
        ),
    ]
