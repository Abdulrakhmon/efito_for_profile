import base64
import io
import locale
import os

import qrcode
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import xlwt
from PyPDF2 import PdfFileReader, PdfFileWriter
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.urls import reverse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import datetime
import json

import pandas as pd
from django.contrib.auth.models import Group, Permission
from administration.models import Country, Region, Point, Unit, User, HSCode, District, Organization, Balance, \
    IntegrationData, ContractPayment, Refund, Integration
from administration.statuses import Languages, ContentTypes, CustomerType, TransPortTypes, IntegratedDataType, \
    ApplicationStatuses, IKRShipmentStatuses, OrganizationType
from core.settings import proxy_config
from exim.models import IKR, IKRProduct, Pest, PestDistributedCountry, AKD, LocalFSS, ExportFSS, IKRShipment, \
    AKDApplication, PestHSCode, IKRApplication, IKRApplicationStatusStep
from fumigation.models import FumigationInsecticide, FumigationFormula, DisinfectedObject, FumigationChamber, \
    FumigationDeclaration, DisinfectedBuildingType, CertificateOfDisinfestation, InsecticidesMonthlyRemainder
from invoice.models import Invoice, InvoicePayment
from invoice.statuses import InvoiceServices
from lab.models import ImportProtocol, LabChemicalReactive, LabDisposable, LabTestMethod


def seed_countries():
    col_names = ('code', 'name_ru', 'name_en', 'name_local')
    countries = pd.read_csv("static/database_files/countries.csv", sep=",", names=col_names, header=None)
    for index, country in countries.iterrows():
        _, is_new = Country.objects.get_or_create(
            code=country.code,
            name_ru=country.name_ru,
            name_en=country.name_en,
            name_local=country.name_local,
        )
        if is_new:
            print(f'{country.name_en} has been added successfully')
        else:
            print(f'{country.name_en} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_regions():
    col_names = ('pk', 'code', 'name_ru', 'name_en', 'name_local', 'gtk_code', 'tin', 'address',
                 'phone', 'bank_account', 'settlement_account')
    regions = pd.read_csv("static/database_files/regions.csv", sep=",", names=col_names, header=None,
                          dtype={'code': pd.np.str})
    for index, region in regions.iterrows():
        db_region, is_new = Region.objects.get_or_create(
            pk=region.pk
        )
        db_region.name_ru = region.name_ru
        db_region.name_en = region.name_en
        db_region.name_local = region.name_local
        db_region.code = region.code
        db_region.gtk_code = region.gtk_code
        db_region.tin = region.tin
        db_region.address = region.address
        db_region.phone = region.phone
        db_region.bank_account = region.bank_account
        db_region.settlement_account = region.settlement_account
        db_region.save()
        if is_new:
            print(f'{db_region.name_en} has been added successfully')
        else:
            print(f'{db_region.name_en} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_districts():
    col_names = ('pk', 'region_name_ru', 'region_name_en', 'region_name_uz', 'code', 'time', 'region_id')
    districts = pd.read_csv("static/database_files/districts.csv", sep=",", names=col_names, header=None)
    for index, district in districts.iterrows():
        db_district, is_new = District.objects.get_or_create(
            pk=int(district.pk)
        )
        db_district.name_ru = district.region_name_ru
        db_district.name_en = district.region_name_en
        db_district.name_local = district.region_name_uz
        db_district.region_id = int(district.region_id)
        db_district.save()
        if is_new:
            print(f'{db_district.name_en} has been added successfully')
        else:
            print(f'{db_district.name_en} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_points():
    col_names = ('pk', 'region_pk', 'name_ru', 'name_en', 'name_local', 'type', 'code')
    points = pd.read_csv("static/database_files/points.csv", sep=",", names=col_names, header=None,
                         dtype={'code': pd.np.str})
    is_new = False
    for index, point in points.iterrows():
        if pd.isnull(point.pk):
            Point.objects.create(
                region_id=point.region_pk,
                name_ru=point.name_ru,
                name_en=point.name_en,
                name_local=point.name_local,
                type=point.type,
                code=point.code if not pd.isnull(point.code) else None
            )
        else:
            db_point, is_new = Point.objects.get_or_create(
                pk=point.pk,
            )
            db_point.region_id = point.region_pk
            db_point.name_ru = point.name_ru
            db_point.name_en = point.name_en
            db_point.name_local = point.name_local
            db_point.type = point.type
            db_point.code = point.code if not pd.isnull(point.code) else None
            db_point.save()
        if is_new:
            print(f'{point.name_en} has been added successfully')
        else:
            print(f'{point.name_en} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_units():
    col_names = ('code', 'name_ru', 'description')
    units = pd.read_csv("static/database_files/units.csv", sep=",", names=col_names, header=None,
                        dtype={'code': pd.np.str})
    for index, unit in units.iterrows():
        _, is_new = Unit.objects.get_or_create(
            code=unit.code,
            name_ru=unit.name_ru,
            name_en=unit.name_ru,
            name_local=unit.name_ru,
            description=unit.description
        )
        if is_new:
            print(f'{unit.name_ru} has been added successfully')
        else:
            print(f'{unit.name_ru} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_permission_groups():
    # akd_inspector_permissions = (
    #     'list_republic_ikr', 'view_republic_ikr', 'add_point_ikrshipment', 'list_point_ikrshipment',
    #     'delete_inspector_ikrshipment', 'change_inspector_ikrshipment', 'add_point_transit', 'delete_inspector_transit',
    #     'add_point_tbotd', 'delete_inspector_tbotd', 'list_point_tbotd', 'view_point_tbotd', 'add_point_akd',
    #     'delete_inspector_akd', 'list_republic_akd', 'view_republic_akd', 'add_point_provided_service',
    #     'list_region_fss', 'add_region_fss', 'view_republic_fss'
    # )
    # akd_inspectors_group, _ = Group.objects.get_or_create(name='AKD Inspectors')
    # akd_inspectors_group.permissions.clear()
    # for permission in akd_inspector_permissions:
    #     print(permission)
    #     akd_inspectors_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # local_fss_inspector_permissions = (
    #     'list_local_fss', 'add_local_fss', 'delete_local_fss'
    # )
    # local_fss_inspectors_group, _ = Group.objects.get_or_create(name='Local FSS Inspectors')
    # local_fss_inspectors_group.permissions.clear()
    # for permission in local_fss_inspector_permissions:
    #     print(permission)
    #     local_fss_inspectors_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # local_agronomists_permissions = (
    #     'add_region_given_blanks', 'delete_region_given_blanks', 'list_region_given_blanks', 'list_region_local_fss'
    # )
    # local_agronomists_group, _ = Group.objects.get_or_create(name='Local Agronomists')
    # local_agronomists_group.permissions.clear()
    # for permission in local_agronomists_permissions:
    #     print(permission)
    #     local_agronomists_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # region_managers_permissions = (
    #     'list_republic_ikr', 'view_republic_ikr', 'list_republic_akd', 'view_republic_akd', 'list_region_tbotd',
    #     'view_region_tbotd', 'list_region_transit', 'list_region_given_blanks',
    #     'list_region_fss', 'view_republic_fss', 'list_region_local_fss'
    # )
    # region_managers_group, _ = Group.objects.get_or_create(name='Region managers')
    # region_managers_group.permissions.clear()
    # for permission in region_managers_permissions:
    #     print(permission)
    #     region_managers_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # republic_managers_permissions = (
    #     'list_republic_ikr', 'view_republic_ikr', 'list_republic_akd', 'view_republic_akd', 'list_republic_tbotd',
    #     'view_republic_tbotd', 'list_republic_transit', 'list_republic_given_blanks', 'list_republic_fss',
    #     'view_republic_fss'
    # )
    # republic_managers_group, _ = Group.objects.get_or_create(name='Republic managers')
    # republic_managers_group.permissions.clear()
    # for permission in republic_managers_permissions:
    #     print(permission)
    #     republic_managers_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # accountant_permissions = (
    #     'list_republic_ikr', 'view_republic_ikr', 'list_republic_akd', 'view_republic_akd',
    #     'list_point_tbotd', 'view_point_tbotd', 'list_region_invoice', 'view_region_invoice',
    #     'add_region_invoice_payment', 'add_region_invoice_refund', 'list_region_fss', 'list_region_local_fss'
    # )
    # accountants_group, _ = Group.objects.get_or_create(name='Accountants')
    # accountants_group.permissions.clear()
    # for permission in accountant_permissions:
    #     print(permission)
    #     accountants_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # operator_permissions = (
    #     'list_republic_ikr', 'view_republic_ikr', 'list_region_invoice', 'list_region_akd', 'view_republic_akd',
    #     'view_region_invoice', 'add_region_provided_service'
    # )
    # operator_group, _ = Group.objects.get_or_create(name='Operator')
    # operator_group.permissions.clear()
    # for permission in operator_permissions:
    #     print(permission)
    #     operator_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # central_lab_import_registerer_permissions = (
    #     'list_republic_ikr', 'view_republic_ikr', 'list_republic_akd',
    #     'view_republic_akd', 'list_republic_tbotd', 'view_republic_tbotd',
    #     'list_republic_import_shortcut', 'view_republic_import_shortcut', 'add_republic_import_shortcut'
    # )
    # central_lab_import_registerer_group, _ = Group.objects.get_or_create(name='Central Lab Import Registerer')
    # central_lab_import_registerer_group.permissions.clear()
    # for permission in central_lab_import_registerer_permissions:
    #     print(permission)
    #     central_lab_import_registerer_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # republic_manager_fumigator_permissions = (
    #     'list_republic_certificate_of_disinfestation',
    # )
    # republic_manager_fumigator_group, _ = Group.objects.get_or_create(name='Republic Manager Fumigator')
    # republic_manager_fumigator_group.permissions.clear()
    # for permission in republic_manager_fumigator_permissions:
    #     print(permission)
    #     republic_manager_fumigator_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # region_manager_fumigator_permissions = (
    #     'list_region_certificate_of_disinfestation',
    # )
    # region_manager_fumigator_group, _ = Group.objects.get_or_create(name='Region Manager Fumigator')
    # region_manager_fumigator_group.permissions.clear()
    # for permission in region_manager_fumigator_permissions:
    #     print(permission)
    #     region_manager_fumigator_group.permissions.add(Permission.objects.get(codename=permission))
    #
    # fumigator_permissions = (
    #     'list_fumigator_certificate_of_disinfestation', 'add_certificate_of_disinfestation',
    #     'edit_certificate_of_disinfestation', 'delete_certificate_of_disinfestation'
    # )
    # fumigator_group, _ = Group.objects.get_or_create(name='Fumigator')
    # fumigator_group.permissions.clear()
    # for permission in fumigator_permissions:
    #     print(permission)
    #     fumigator_group.permissions.add(Permission.objects.get(codename=permission))
    ikr_considered_user_group, created = Group.objects.get_or_create(name='IKR Considered User')
    ikr_considered_user_permissions = (
        'list_republic_ikr', 'view_republic_ikr', 'add_republic_ikr', 'consider_ikr_renewal_application',
        'list_ikr_renewal_application'
    )
    ikr_considered_user_group.permissions.clear()
    for permission in ikr_considered_user_permissions:
        print(permission)
        ikr_considered_user_group.permissions.add(Permission.objects.get(codename=permission))


def seed_users():
    col_names = ('region_id', 'name_ru', 'name_en',
                 'name_local', 'phone', 'point_id')
    users = pd.read_csv("static/database_files/users.csv", sep=",", names=col_names, header=None)

    for index, user in users.iterrows():
        if user.point_id == '0' or user.point_id == 0:
            continue
        try:
            new_user, is_new = User.objects.get_or_create(
                username=f'i{user.phone}',
                name_ru=user.name_ru,
                name_en=user.name_en,
                name_local=user.name_local,
                phone=user.phone,
                point_id=user.point_id
            )
            new_user.set_password(user.phone)
            new_user.role = new_user.point.type
            # new_user.groups.add(akd_inspectors_group)
            new_user.save()
        except:
            continue
        if is_new:
            print(f'{user.phone} has been added successfully')
        else:
            print(f'{user.phone} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_fumigators():
    users = pd.read_excel('static/database_files/fumigators.xlsx')
    for i in users.index:
        name_en = users['name_en'][i]
        name_ru = users['name_ru'][i]
        name_local = users['name_local'][i]
        phone = str(int(users['phone'][i]))
        tin = str(users['tin'][i])
        point_code = str(users['point_code'][i])
        if len(point_code) == 4:
            point_code = '0' + point_code
        point = Point.objects.get(code=point_code)
        # print(name_en + '<->' + name_ru + '<->' + name_local + '<->' + phone + '<->' + tin + '<->' + point_code)
        try:
            new_user, is_new = User.objects.get_or_create(
                username=f'f{phone}',
                name_ru=name_ru,
                name_en=name_en,
                name_local=name_local,
                tin=tin,
                phone=phone,
                point=point
            )
            new_user.set_password(phone)
            new_user.save()
        except:
            continue
        if is_new:
            print(f'{phone} has been added successfully')
        else:
            print(f'{phone} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_groups_to_users():
    users = User.objects.filter(username__startswith='i')
    local_fss_inspectors = Group.objects.get(name='Local FSS Inspectors')
    for user in users:
        if not user.groups.filter(name='Local FSS Inspectors').exists():
            local_fss_inspectors.user_set.add(user)


def seed_groups_to_fumigators():
    users = User.objects.filter(username__startswith='f')
    fumigators = Group.objects.get(name='Fumigator')
    for user in users:
        if not user.groups.filter(name='Fumigator').exists():
            fumigators.user_set.add(user)


def seed_hs_codes():
    col_names = ('code', 'name', 'description')
    hs_codes = pd.read_csv("static/database_files/hs_codes.csv", sep=",", names=col_names, header=None,
                           dtype={'code': pd.np.str})
    for index, hs_code in hs_codes.iterrows():
        # try:
        code = str(hs_code.code)
        length_of_code = len(code)
        code = code.rjust(10 - length_of_code + length_of_code, '0')
        new_hs_code, is_new = HSCode.objects.get_or_create(
            code=code,
            name=hs_code.name,
            description=hs_code.description
        )
        # except:
        #     continue
        if is_new:
            print(f'{hs_code.code} has been added successfully')
        else:
            print(f'{hs_code.code} could not be added, any error occurred or it is already exist!!!!!!!!!!!')

    col_names = ('code', 'name', 'description')
    hs_codes = pd.read_csv("static/database_files/lab_hs_codes.csv", sep=",", names=col_names, header=None,
                           dtype={'code': pd.np.str})
    for index, hs_code in hs_codes.iterrows():
        # try:
        code = str(hs_code.code)
        length_of_code = len(code)
        code = code.rjust(10 - length_of_code + length_of_code, '0')
        try:
            db_hs_code = HSCode.objects.get(code=code)
            db_hs_code.is_lab = True
            db_hs_code.save()
            print(f'{code} success')
        except HSCode.DoesNotExist:
            print(f'{code} not found')
            continue


def seed_lab_hs_codes():
    col_names = ('code',)
    hs_codes = pd.read_csv("static/database_files/lab_hs_codes.csv", sep=",", names=col_names, header=None,
                           dtype={'code': pd.np.str})
    for index, hs_code in hs_codes.iterrows():
        print('hs_code')
        print(hs_code)
        print('hs_code.code')
        print(hs_code.code)
        code = str(hs_code.code)
        length_of_code = len(code)
        code = code.rjust(10 - length_of_code + length_of_code, '0')
        try:
            db_hs_code = HSCode.objects.get(code=code)
            db_hs_code.is_lab = True
            db_hs_code.save()
            print(f'{code} success')
        except HSCode.DoesNotExist:
            print(f'{code} not found')
            continue


def seed_high_risk_hs_codes():
    col_names = ('code',)
    hs_codes = pd.read_csv("static/database_files/high_risk.csv", sep=",", names=col_names, header=None,
                           dtype={'code': pd.np.str})
    for index, hs_code in hs_codes.iterrows():
        print('hs_code')
        print(hs_code)
        print('hs_code.code')
        print(hs_code.code)
        code = str(hs_code.code)
        try:
            db_hs_codes = HSCode.objects.filter(code__startswith=code)
            for db_hs_code in db_hs_codes:
                db_hs_code.is_high_risked = True
                db_hs_code.save()
                print(f'{db_hs_code.code} success')
        except Exception as e:
            print(f'{e}')
            continue


def seed_ikrs():
    col_names = ('request_number', 'language', 'request_date', 'number', 'given_date',
                 'expire_date', 'importer_type', 'importer_tin',
                 'importer_name', 'importer_representative_name',
                 'importer_region__code', 'importer_address', 'importer_phone_number',
                 'exporter_organization_name', 'exporter_country__code', 'exporter_address',
                 'transport_method', 'route', 'point', 'undertaken_quarantine',
                 'extra_requirement', 'signatory', 'is_approved')
    ikrs = pd.read_csv("static/database_files/ikrs.csv", sep=",", names=col_names, header=None)
    for index, ikr in ikrs.iterrows():
        try:
            application_region_pk = Region.objects.values_list('pk', flat=True).get(code=ikr.importer_region__code)
            exporter_country_id = Country.objects.values_list('pk', flat=True).get(code=ikr.exporter_country__code)
            new_ikr, is_new = IKR.objects.get_or_create(
                request_number=ikr.request_number,
                language=Languages.LANGUAGE_DICT.get(ikr.language) or Languages.RUSSIAN,
                request_date=datetime.datetime.strptime(ikr.request_date, '%Y-%m-%d').date(),
                number=ikr.number,
                given_date=datetime.datetime.strptime(ikr.request_date, '%Y-%m-%d').date(),
                expire_date=datetime.datetime.strptime(ikr.expire_date, '%Y-%m-%d').date(),
                importer_type=int(ikr.importer_type),
                importer_tin=ikr.importer_tin,
                importer_name=ikr.importer_name,
                importer_representative_name=ikr.importer_representative_name,
                importer_region_id=application_region_pk,
                importer_address=ikr.importer_address,
                importer_phone_number=ikr.importer_phone_number,
                exporter_organization_name=ikr.exporter_organization_name,
                exporter_country_id=exporter_country_id,
                exporter_address=ikr.exporter_address,
                transport_method=int(ikr.transport_method),
                route=ikr.route,
                point_id=5,
                undertaken_quarantine=ikr.undertaken_quarantine,
                extra_requirement=ikr.extra_requirement,
                signatory=ikr.signatory,
                is_approved=True if ikr.is_approved == 'Y' else False
            )
        except:
            continue
        if is_new:
            print(f'{ikr.number} has been added successfully')
        else:
            print(f'{ikr.number} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_ikr_products():
    col_names = ('request_number', 'hs_code', 'name', 'quantity', 'unit_code')
    products = pd.read_csv("static/database_files/products.csv", sep=",", names=col_names, header=None)
    for index, product in products.iterrows():
        try:
            hs_code_pk = HSCode.objects.values_list('pk', flat=True).get(code=product.hs_code)
            product.name = product[2]
            ikr_pk = IKR.objects.values_list('pk', flat=True).get(request_number=product.request_number)
            unit_pk = Unit.objects.values_list('pk', flat=True).get(code=product.unit_code)
            new_product, is_new = IKRProduct.objects.get_or_create(
                ikr_id=ikr_pk,
                name=product.name,
                hs_code_id=hs_code_pk,
                quantity=product.quantity,
                unit_id=unit_pk
            )
        except:
            print(f'HS Code {product.hs_code} was not found in our database')
            continue
        if is_new:
            print(f'{new_product.name} has been added successfully')
        else:
            print(f'{new_product.name} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_pests():
    with open("static/database_files/pests.json") as json_file:
        data = json.load(json_file)
        not_found_counter = 0
        country_counter = 0
        for pest in data.get('pests'):
            new_pest, is_new = Pest.objects.get_or_create(
                name_ru=pest.get('pest_name'),
                damaged_plants_in_ru=pest.get('damaged_plants'),
                damaged_plant_parts_in_ru=pest.get('damaged_plant_parts'),
                penetrating_ways_in_ru=pest.get('penetrating_ways')
            )
            countries = pest.get('pest_distributed_countries').split(',')
            country_counter += len(countries)
            print(pest)
            for country in countries:
                country = Country.objects.filter(name_ru=country.strip())
                print(country)
                if country:
                    country = country.first()
                    related_country, is_new = PestDistributedCountry.objects.get_or_create(
                        pest=new_pest,
                        country=country
                    )


def seed_organizations():
    # col_names = ('organization_name', 'organization_tin')
    # organizations = pd.read_csv("static/database_files/new_orgs2.csv", sep=",", names=col_names, header=None)
    # for index, organization in organizations.iterrows():
    #     try:
    #         exist_organization = Organization.objects.get(tin=organization.organization_tin)
    #         print(f'{exist_organization.tin} is already exist.')
    #     except Organization.DoesNotExist:
    #         new_organization, is_new = Organization.objects.get_or_create(
    #             name=organization.organization_name,
    #             tin=int(organization.organization_tin)
    #         )
    #         if is_new:
    #             print(f'{new_organization.name} has been added successfully')
    #         else:
    #             print(f'{new_organization.name} could not be added, any error occurred or it is already exist!!!!!!!!!!!')
    # users = User.objects.filter(Q(username__startswith='i') | Q(username__startswith='f'))
    # for user in users:
    #     if user.tin:
    #         try:
    #             organization = Organization.objects.get(tin=user.tin)
    #             print(f'{organization.tin} is already exist!!!!!!!!!!!')
    #         except Organization.DoesNotExist:
    #             Organization.objects.create(
    #                 name=user.name_ru,
    #                 tin=user.tin
    #             )
    #             print(f'{user.name_ru} has been added successfully')

    # certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(given_date__gte='2022-01-01')
    # for certificate_of_disinfestation in certificates_of_disinfestation:
    #     if not certificate_of_disinfestation.organization_tin or len(certificate_of_disinfestation.organization_tin) < 9:
    #         certificate_of_disinfestation.organization_tin = certificate_of_disinfestation.fumigator.tin
    #         certificate_of_disinfestation.save()

    local_fsses = LocalFSS.objects.filter(given_date__gte='2022-01-01')
    for local_fss in local_fsses:
        if local_fss.applicant_tin:
            try:
                organiztion = Organization.objects.get(tin=local_fss.applicant_tin)
            except Organization.DoesNotExist:
                local_fss.applicant_tin = local_fss.inspector.tin
                local_fss.save()


def seed_balances():
    first_day_of_month = '2022-01-01'
    service_type = None
    organizations = Organization.objects.all()
    regions = Region.objects.all()
    for organization in organizations:
        tin = organization.tin
        for region in regions:
            balances = Balance.objects.filter(organization=organization, month=first_day_of_month, region=region)

            balance_in_services = {'КP': 0, 'Лаборатория': 0, 'АКД': 0, 'Фумигация': 0, 'ФСС': 0, 'Вн_ФСС': 0, 'Лаборатория': 0}

            invoices_payments = InvoicePayment.objects.confirmed().filter(invoice__applicant_tin=tin,
                                                                          invoice__region=region,
                                                                          payment_date__gte=first_day_of_month)
            contract_payments = ContractPayment.objects.filter(organization=organization, region=region,
                                                               payment_date__gte=first_day_of_month)
            refunds = Refund.objects.filter(organization=organization, region=region,
                                            refunded_date__gte=first_day_of_month)
            if balances or invoices_payments or contract_payments:
                for key in balance_in_services:
                    amount = 0
                    service_amount = 0
                    balance = 0
                    refund_amount = 0
                    if key == 'КP' and int(region.pk) == 15:
                        service_type = InvoiceServices.IKR
                        ikrs = IKR.objects.filter(importer_tin=tin, given_date__gte=first_day_of_month).order_by(
                            '-given_date')
                        balance = balances.filter(service_type=service_type).first()
                        if balance:
                            amount = balance.amount
                        else:
                            amount = 0
                        invoice_amount = \
                        invoices_payments.filter(invoice__service_type=service_type).aggregate(Sum('payment_amount'))[
                            'payment_amount__sum']
                        if invoice_amount:
                            amount = amount + invoice_amount

                        contract_payment_amount = \
                        contract_payments.filter(service_type=service_type).aggregate(Sum('payment_amount'))['payment_amount__sum']
                        if contract_payment_amount:
                            amount = amount + contract_payment_amount

                        refund_amount = refunds.filter(service_type=service_type).aggregate(Sum('amount'))['amount__sum']
                        if refund_amount:
                            amount = amount - refund_amount
                        if ikrs:
                            service_amount = ikrs.aggregate(Sum('payment_amount'))['payment_amount__sum']
                        amount = amount - service_amount
                    if key == 'АКД':
                        service_type = InvoiceServices.TBOTD
                        balance = balances.filter(service_type=service_type).first()
                        if balance:
                            amount = balance.amount
                        else:
                            amount = 0
                        invoice_amount = \
                        invoices_payments.filter(invoice__service_type=service_type).aggregate(Sum('payment_amount'))[
                            'payment_amount__sum']
                        if invoice_amount:
                            amount = amount + invoice_amount

                        contract_payment_amount = \
                        contract_payments.filter(service_type=service_type).aggregate(Sum('payment_amount'))['payment_amount__sum']
                        if contract_payment_amount:
                            amount = amount + contract_payment_amount

                        refund_amount = refunds.filter(service_type=service_type).aggregate(Sum('amount'))['amount__sum']
                        if refund_amount:
                            amount = amount - refund_amount

                        akds = AKD.objects.filter(tbotd__ikr_shipment__ikr__point__region=region,
                                                  tbotd__ikr_shipment__ikr__importer_tin=tin,
                                                  given_date__gte=first_day_of_month).order_by('-given_date')
                        if akds:
                            service_amount = akds.aggregate(Sum('payment_amount'))['payment_amount__sum']

                        amount = amount - service_amount
                    if key == 'Фумигация':
                        service_type = InvoiceServices.FUMIGATION
                        balance = balances.filter(service_type=service_type).first()
                        if balance:
                            amount = balance.amount
                        else:
                            amount = 0
                        invoice_amount = \
                        invoices_payments.filter(invoice__service_type=service_type).aggregate(Sum('payment_amount'))[
                            'payment_amount__sum']
                        if invoice_amount:
                            amount = amount + invoice_amount

                        contract_payment_amount = \
                        contract_payments.filter(service_type=service_type).aggregate(Sum('payment_amount'))['payment_amount__sum']
                        if contract_payment_amount:
                            amount = amount + contract_payment_amount

                        refund_amount = refunds.filter(service_type=service_type).aggregate(Sum('amount'))['amount__sum']
                        if refund_amount:
                            amount = amount - refund_amount

                        certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(
                            organization_tin=tin,
                            region=region,
                            given_date__gte=first_day_of_month)
                        if certificates_of_disinfestation:
                            service_amount = certificates_of_disinfestation.aggregate(Sum('total_price'))[
                                'total_price__sum']
                        amount = amount - service_amount
                    if key == 'ФСС':
                        service_type = InvoiceServices.FSS
                        balance = balances.filter(service_type=service_type).first()
                        if balance:
                            amount = balance.amount
                        else:
                            amount = 0

                        invoice_amount = \
                        invoices_payments.filter(invoice__service_type=service_type).aggregate(Sum('payment_amount'))[
                            'payment_amount__sum']
                        if invoice_amount:
                            amount = amount + invoice_amount

                        contract_payment_amount = \
                        contract_payments.filter(service_type=service_type).aggregate(Sum('payment_amount'))['payment_amount__sum']
                        if contract_payment_amount:
                            amount = amount + contract_payment_amount

                        refund_amount = refunds.filter(service_type=service_type).aggregate(Sum('amount'))['amount__sum']
                        if refund_amount:
                            amount = amount - refund_amount

                        export_fsses = ExportFSS.all_objects.filter(region=region, exporter_tin=tin,
                                                                    given_date__gte=first_day_of_month).order_by(
                            '-given_date')
                        if export_fsses:
                            service_amount = export_fsses.aggregate(Sum('payment_amount'))['payment_amount__sum']
                        amount = amount - service_amount
                    if key == 'Вн_ФСС':
                        service_type = InvoiceServices.LocalFSS
                        local_fsses = LocalFSS.objects.filter(sender_region=region, applicant_tin=tin,
                                                              given_date__gte=first_day_of_month).order_by(
                            '-given_date')
                        balance = balances.filter(service_type=service_type).first()
                        if balance:
                            amount = balance.amount
                        else:
                            amount = 0

                        invoice_amount = \
                        invoices_payments.filter(invoice__service_type=service_type).aggregate(Sum('payment_amount'))[
                            'payment_amount__sum']
                        if invoice_amount:
                            amount = amount + invoice_amount

                        contract_payment_amount = \
                        contract_payments.filter(service_type=service_type).aggregate(Sum('payment_amount'))['payment_amount__sum']
                        if contract_payment_amount:
                            amount = amount + contract_payment_amount

                        refund_amount = refunds.filter(service_type=service_type).aggregate(Sum('amount'))['amount__sum']
                        if refund_amount:
                            amount = amount - refund_amount
                        if local_fsses:
                            service_amount = local_fsses.aggregate(Sum('payment_amount'))['payment_amount__sum']
                        amount = amount - service_amount
                    if key == 'Лаборатория':
                        service_type = InvoiceServices.LAB
                        service_amount = 0
                        import_protocols = ImportProtocol.objects.filter(point__region=region,
                                                                         shortcut__ikr__importer_tin=tin,
                                                                         given_date__gte=first_day_of_month).order_by(
                            '-given_date')
                        balance = balances.filter(service_type=service_type).first()
                        if balance:
                            amount = balance.amount
                        else:
                            amount = 0

                        invoice_amount = invoices_payments.filter(invoice__service_type=service_type).aggregate(
                            Sum('payment_amount'))['payment_amount__sum']
                        if invoice_amount:
                            amount = amount + invoice_amount

                        contract_payment_amount = \
                        contract_payments.filter(service_type=service_type).aggregate(Sum('payment_amount'))[
                            'payment_amount__sum']
                        if contract_payment_amount:
                            amount = amount + contract_payment_amount

                        refund_amount = refunds.filter(service_type=service_type).aggregate(Sum('amount'))[
                            'amount__sum']
                        if refund_amount:
                            amount = amount - refund_amount
                        if import_protocols:
                            service_amount = import_protocols.aggregate(Sum('payment_amount'))['payment_amount__sum']
                        amount = amount - service_amount

                    if key == 'КP' and int(region.pk) != 15:
                        pass
                    else:
                        Balance.objects.get_or_create(
                            organization=organization,
                            region=region,
                            service_type=service_type,
                            amount=amount,
                            month='2022-01-01',
                            registrar=User.objects.get(username='admin')
                        )
                        print('organization')
                        print(region.name_ru)
                        print(organization.name)
                        print(service_type)
                        print(amount)
    # col_names = ('inn', 'debit', 'kredit', 'service_type', 'region')
    # balances = pd.read_csv("static/database_files/balance_agust_sam.csv", sep=",", names=col_names, header=None)
    # for index, balance in balances.iterrows():
    #     try:
    #         organization = Organization.objects.get(tin=int(balance.inn))
    #     except Organization.DoesNotExist:
    #         organization = None
    #
    #     if organization:
    #         region = Region.objects.get(pk=balance.region)
    #         # try:
    #         #     if balance.region == 'нукус':
    #         #         region = Region.objects.get(pk=1)
    #         #     elif balance.region == 'Андижон':
    #         #         region = Region.objects.get(pk=2)
    #         #     elif balance.region == 'Бухоро':
    #         #         region = Region.objects.get(pk=3)
    #         #     elif balance.region == 'Жиззах':
    #         #         region = Region.objects.get(pk=4)
    #         #     elif balance.region == 'Кашкадарё':
    #         #         region = Region.objects.get(pk=5)
    #         #     elif balance.region == 'навоий':
    #         #         region = Region.objects.get(pk=6)
    #         #     elif balance.region == 'наманган':
    #         #         region = Region.objects.get(pk=7)
    #         #     elif balance.region == 'самарканд':
    #         #         region = Region.objects.get(pk=8)
    #         #     elif balance.region == 'Сурхондарё':
    #         #         region = Region.objects.get(pk=9)
    #         #     elif balance.region == 'сирдарё':
    #         #         region = Region.objects.get(pk=10)
    #         #     elif balance.region == 'Тошвил':
    #         #         region = Region.objects.get(pk=11)
    #         #     elif balance.region == 'Фаргона':
    #         #         region = Region.objects.get(pk=12)
    #         #     elif balance.region == 'хоразм':
    #         #         region = Region.objects.get(pk=13)
    #         #     elif balance.region == 'тошкент':
    #         #         region = Region.objects.get(pk=14)
    #         # except Region.DoesNotExist:
    #         #     print(balance.region)
    #
    #         if balance.service_type == 'АКД':
    #             service_type = 2
    #         elif balance.service_type == 'АкдФСС':
    #             service_type = 2
    #         elif balance.service_type == 'Фумигация':
    #             service_type = 3
    #         elif balance.service_type == 'ФСС':
    #             service_type = 4
    #         elif balance.service_type == 'ВнФСС':
    #             service_type = 5
    #         else:
    #             print('*****************')
    #             print(balance.service_type)
    #             print('*****************')
    #
    #         if float(balance.debit) > float(balance.kredit):
    #             amount = -1 * float(balance.debit)
    #         else:
    #             amount = balance.kredit
    #
    #         month = datetime.datetime(2020, 8, 1)
    #
    #         try:
    #             registrar = User.objects.get(username='admin')
    #         except Region.DoesNotExist:
    #             print('User with admin user name does not exist.')
    #
    #         new_balance, is_new = Balance.objects.get_or_create(
    #             organization=organization,
    #             region=region,
    #             service_type=service_type,
    #             amount=amount,
    #             month=month,
    #             registrar=registrar
    #         )
    #         if is_new:
    #             print(f'has been added successfully')
    #         else:
    #             print(f'could not be added, any error occurred or it is already exist!!!!!!!!!!!')
    #     else:
    #         print(f'Organization not found')


def seed_organizations_in_invoice():
    organizations_in_invoice = Invoice.objects.order_by('applicant_tin').distinct('applicant_tin')
    print('distinct_organizations')
    print(organizations_in_invoice.count())

    for organization_in_invoice in organizations_in_invoice:
        applicant_organization = ''
        if organization_in_invoice.applicant_organization:
            applicant_organization = organization_in_invoice.applicant_organization
        else:
            applicant_organization = organization_in_invoice.applicant_fullname
        try:
            organization = Organization.objects.get(tin=organization_in_invoice.applicant_tin)
            print(f'{organization.tin} is already exist!!!!!!!!!!!')
        except Organization.DoesNotExist:
            Organization.objects.create(
                name=applicant_organization,
                tin=organization_in_invoice.applicant_tin
            )
            print(f'{organization_in_invoice.applicant_tin} has been added successfully')


def seed_insecticides():
    col_names = (
        'formula_id', 'fumigation_formula_id', 'formula_name', 'registrar_id', 'formula_status', 'formula_date')
    insecticides = pd.read_csv("static/database_files/fumigation_insecticide.csv", sep=",", names=col_names,
                               header=None)
    for index, insecticide in insecticides.iterrows():
        is_active = True
        print('head')
        formula_id = insecticide.formula_id
        fumigation_formula_id = insecticide.fumigation_formula_id
        formula_name = insecticide.formula_name
        registrar_id = insecticide.registrar_id
        formula_status = insecticide.formula_status
        formula_date = insecticide.formula_date
        print('end')
        if int(formula_status) == 0:
            is_active = False
        new_insecticide, is_new = FumigationInsecticide.objects.get_or_create(
            id=int(formula_id),
            formula=FumigationFormula.objects.get(pk=fumigation_formula_id),
            name=formula_name,
            is_active=is_active
        )
        if is_new:
            print(f'{new_insecticide.name} has been added successfully')
        else:
            print(f'{new_insecticide.name} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def disinfected_objects():
    col_names = ('disinfected_object_id', 'disinfected_object_name', 'registrar_id', 'disinfected_object_date')
    disinfected_objects = pd.read_csv("static/database_files/disinfected_objects.csv", sep=",", names=col_names,
                                      header=None)
    for index, disinfected_object in disinfected_objects.iterrows():
        print('head')
        disinfected_object_id = disinfected_object.disinfected_object_id
        disinfected_object_name = disinfected_object.disinfected_object_name
        registrar_id = disinfected_object.registrar_id
        disinfected_object_date = disinfected_object.disinfected_object_date
        print('end')
        new_disinfected_object, is_new = DisinfectedObject.objects.get_or_create(
            id=int(disinfected_object_id),
            name=disinfected_object_name,
            is_active=True
        )
        if is_new:
            print(f'{new_disinfected_object.name} has been added successfully')
        else:
            print(
                f'{new_disinfected_object.name} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def fumigation_chamber():
    col_names = ('fumigation_chamber_id', 'region_id', 'fumigation_chamber_number', 'fumigation_chamber_date')
    fumigation_chambers = pd.read_csv("static/database_files/fumigation_chambers.csv", sep=",", names=col_names,
                                      header=None)
    for index, fumigation_chamber in fumigation_chambers.iterrows():
        is_active = True
        print('head')
        fumigation_chamber_id = fumigation_chamber.fumigation_chamber_id
        region_id = fumigation_chamber.region_id
        fumigation_chamber_number = fumigation_chamber.fumigation_chamber_number
        fumigation_chamber_date = fumigation_chamber.fumigation_chamber_date
        print('end')
        new_fumigation_chamber, is_new = FumigationChamber.objects.get_or_create(
            id=int(fumigation_chamber_id),
            region=Region.objects.get(pk=region_id),
            number=fumigation_chamber_number,
            is_active=is_active
        )
        if is_new:
            print(f'{new_fumigation_chamber.number} has been added successfully')
        else:
            print(
                f'{new_fumigation_chamber.number} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def fumigation_declaration():
    col_names = (
        'fumigation_declaration_id', 'formula_id', 'fumigation_declaration_name', 'fumigation_declaration_description',
        'price', 'registrar_id', 'fumigation_declaration_date')
    fumigation_declarations = pd.read_csv("static/database_files/fumigation_declaration.csv", sep=",", names=col_names,
                                          header=None)
    for index, fumigation_declaration in fumigation_declarations.iterrows():
        print('head')
        fumigation_declaration_id = fumigation_declaration.fumigation_declaration_id
        formula_id = fumigation_declaration.formula_id
        fumigation_declaration_name = fumigation_declaration.fumigation_declaration_name
        fumigation_declaration_description = fumigation_declaration.fumigation_declaration_description
        price = fumigation_declaration.price
        registrar_id = fumigation_declaration.registrar_id
        fumigation_declaration = fumigation_declaration.fumigation_declaration_date
        print('end')
        new_fumigation_declaration, is_new = FumigationDeclaration.objects.get_or_create(
            id=int(fumigation_declaration_id),
            name=fumigation_declaration_name,
            description=fumigation_declaration_description,
            price=price,
            is_active=True
        )
        if is_new:
            print(f'{new_fumigation_declaration.name} has been added successfully')
        else:
            print(
                f'{new_fumigation_declaration.name} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def disinfected_building_type():
    col_names = ('name_ru', 'name_en')
    disinfected_building_types = pd.read_csv("static/database_files/disinfected_building_type.csv", sep=",",
                                             names=col_names, header=None)
    for index, disinfected_building_type in disinfected_building_types.iterrows():
        print('head')
        name_ru = disinfected_building_type.name_ru
        name_en = disinfected_building_type.name_en
        print('end')
        new_disinfected_building_type, is_new = DisinfectedBuildingType.objects.get_or_create(
            name_ru=name_ru,
            name_en=name_en,
            name_local=name_ru
        )
        if is_new:
            print(f'{new_disinfected_building_type.name_ru} has been added successfully')
        else:
            print(
                f'{new_disinfected_building_type.name_ru} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def certificates_of_disinfestation():
    f = open('static/database_files/certificates_of_disinfestation.json')
    data = json.load(f)
    f.close()
    print('Bismillarihir Rohmanir Rohim.')
    print(len(data))

    inspector_id = 0
    disinfected_building_type_id = 0
    disinfected_building_type = None
    counter = 0
    country_id = None
    for x in data:
        print("Bismillah")
        print(float(x['certificate_number']))
        print(float(x['insecticide_dosage']))
        if x['disinfected_building_name'] == 'Автотранспорт' or x[
            'disinfected_building_name'] == 'Automobile transport':
            disinfected_building_type = DisinfectedBuildingType.objects.get(name_ru='Автотранспорт')
        elif x['disinfected_building_name'] == 'Палатка':
            disinfected_building_type = DisinfectedBuildingType.objects.get(name_ru='Палатка')
        print(x['country_id'])
        if x['country_id'] == "0":
            print('1111111111')
            country_id = None
        else:
            print('2222222')
            country_id = x['country_id']
        print(country_id)
        if x['inspector_fullname'] == 'Ж Рустамов':
            inspector_id = 385
        elif x['inspector_fullname'] == 'Жуманиёзов Б':
            inspector_id = 259
        elif x['inspector_fullname'] == 'Исамухамедов А' or x['inspector_fullname'] == 'Исамухамедов.А.А':
            inspector_id = 218
        elif x['inspector_fullname'] == 'Маматов О' or x['inspector_fullname'] == 'Маматов О.':
            inspector_id = 319
        elif x['inspector_fullname'] == 'Назиров Ж' or x['inspector_fullname'] == 'Назиров Ж.':
            inspector_id = 316
        elif x['inspector_fullname'] == 'Р Абдуллаев':
            inspector_id = 22
        elif x['inspector_fullname'] == 'Рахмонов С':
            inspector_id = 651
        elif x['inspector_fullname'] == 'Сиддиков У':
            inspector_id = 710
        elif x['inspector_fullname'] == 'Шорахметов Б':
            inspector_id = 225
        elif x['inspector_fullname'] == 'Шукуров С У.' or x['inspector_fullname'] == 'Шукуров С.У.':
            inspector_id = 230
        elif x['inspector_fullname'] == 'Юлдашев С.Б.':
            inspector_id = 237

        new_certificate_of_disinfestation, is_new = CertificateOfDisinfestation.objects.get_or_create(
            region_id=int(x['region_id']),
            district_id=127,
            number=x['certificate_number'],
            given_date=x['certificate_given_date'],
            language=x['lan'],
            type=x['certificate_type'],
            organization_name=x['organization_name'],
            organization_tin=x['organization_inn'],
            country_id=country_id,
            insecticide_id=x['insecticide_id'],
            insecticide_dosage=float(x['insecticide_dosage']),
            insecticide_unit_id=14,
            declaration_price=float(x['price_in_declaration']),
            total_price=float(x['total_price']),
            fumigator_id=int(x['fumigator_id']),
            inspector_id=inspector_id,
            customer=x['customer_fullname'],
            disinfected_building_type=disinfected_building_type,
            disinfected_building_info=x['disinfected_building_info'],
            disinfected_building_volume=int(x['disinfected_building_volume']),
            disinfected_building_unit_id=int(x['disinfected_building_unit']),
            disinfected_product=x['disinfected_product_info'],
            disinfestation_type=1,
            temperature=x['temperature'],
            beginning_of_disinfection=x['beginning_of_disinfection'],
            ending_of_disinfection=x['ending_of_disinfection'],
            degassing_time=x['spent_time'],
            bio_indicator=1,
            disinfection_result=x['disinfection_result'],
            disinfected_object_id=2
        )

        if is_new:
            counter = counter + 1
            print(f'{counter}. {new_certificate_of_disinfestation.number} has been added successfully')


def monthly_remainder_of_insecticides():
    f = open('static/database_files/monthly_remainder_of_insecticides_31072020.json')
    data = json.load(f)
    f.close()
    counter = 0
    for x in data:
        new_insecticides_monthly_remainder, is_new = InsecticidesMonthlyRemainder.objects.get_or_create(
            region_id=int(x['region_id']),
            fumigation_formula_id=int(x['fumigation_formula_id']),
            amount=float(x['amount']),
            end_of_month=x['end_of_month'],
        )

        if is_new:
            counter = counter + 1
            print(f'{counter}. {new_insecticides_monthly_remainder.region_id} has been added successfully')


def delete_synchronised_integrated_data():
    integration_datas = IntegrationData.objects.filter(is_synchronised=True)[:50000]
    for integration_data in integration_datas:
        integration_data.delete()


def mark_free_fsses():
    fsses = ExportFSS.objects.filter(given_date__gte='2020-01-01')
    # free_hs_codes = ['07', '08', '0904', '1202', '5002', '5003', '57']
    for fss in fsses:
        fss_products = fss.products.all()
        is_free = True
        for fss_product in fss_products:
            hs_code = fss_product.hs_code.code
            if hs_code.startswith("07") or hs_code.startswith("08") or hs_code.startswith("0904") or hs_code.startswith(
                    "1202") or hs_code.startswith("5002") or hs_code.startswith("5003") or hs_code.startswith(
                "5004") or hs_code.startswith("5005") or hs_code.startswith("5006") or hs_code.startswith(
                "5007") or hs_code.startswith("5111") or hs_code.startswith("5112") or hs_code.startswith(
                "5113") or hs_code.startswith("5208") or hs_code.startswith("5209") or hs_code.startswith(
                "5210") or hs_code.startswith("5211") or hs_code.startswith("5212") or hs_code.startswith(
                "5309") or hs_code.startswith("5310") or hs_code.startswith("5311") or hs_code.startswith(
                "54") or hs_code.startswith("5512") or hs_code.startswith("5513") or hs_code.startswith(
                "5514") or hs_code.startswith("5515") or hs_code.startswith("5516") or hs_code.startswith(
                "56") or hs_code.startswith("57") or hs_code.startswith("58") or hs_code.startswith(
                "59") or hs_code.startswith("60") or hs_code.startswith("61") or hs_code.startswith(
                "62") or hs_code.startswith("63"):
                is_free = is_free * True
            else:
                is_free = is_free * False
        if is_free:
            fss.payment_amount = 0
            fss.save()


def delete_shipments():
    print('Delete shipments')
    shipments = IKRShipment.objects.filter(akd_application__isnull=True)
    print(len(shipments))
    for shipment in shipments:
        # for shipment_product in shipment.products.all():
        #     ikr_product = shipment_product.ikr_product
        #     ikr_product.remaining_quantity = ikr_product.remaining_quantity + shipment_product.quantity
        #     ikr_product.save()
        # print(f'{shipment.pk}')
        shipment.delete()


def active_deleted_applications():
    akd_applications = AKDApplication.objects.filter(request_number='30744300520200000055')
    for akd_application in akd_applications:
        akd_application.is_active = True
        akd_application.save()


def change_ikr_applications():
    ikr_applications = IKRApplication.objects.exclude(
        Q(status=ApplicationStatuses.ZERO_ONE_NINE) | Q(status=ApplicationStatuses.ONE_ZERO_SIX))
    ikr_applications = ikr_applications.filter(added_at__lt='2021-04-08 00:00:00', is_active=False)
    print('Number of ikr applications')
    print(ikr_applications.count())
    description = 'Отказалась. Попробуй еще раз...'
    count = 0
    user = User.objects.get(username='a201283204')
    for ikr_application in ikr_applications:
        count += 1
        print(f'{count}. ' + str(ikr_application.request_number))
        try:
            ikr = ikr_application.ikr
        except:
            ikr_application.owner = user
            ikr_application.status = ApplicationStatuses.ZERO_ONE_NINE
            ikr_application.is_active = False
            ikr_application.is_paid = False
            ikr_application.save()
            status_json_data = {"KR_ST_Information": {"Information_Date": "",
                                                      "KR_ST": {
                                                          "RQST_NO": "",
                                                          "RQST_DT": "",
                                                          "DOC_FNCT_CD": "",
                                                          "PRICHINA": "",
                                                          "USER_FULL_NAME": "",
                                                          "USER_PHONE": "",
                                                          "USER_ACTION_DATE": "",
                                                          "USER_POSITION": "",
                                                          "USER_INN": "",
                                                          "ORGAN_ID": "",
                                                          "ORGAN_NAME": "",
                                                          "ORGAN_PHONE": ""
                                                      }
                                                      }
                                }
            status_json_data['KR_ST_Information']['Information_Date'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            ikr_st = status_json_data['KR_ST_Information']['KR_ST']
            ikr_st['RQST_NO'] = ikr_application.request_number
            ikr_st['RQST_DT'] = ikr_application.request_date.strftime("%Y-%m-%d")
            ikr_st['USER_FULL_NAME'] = user.name_ru
            ikr_st['USER_PHONE'] = user.phone
            ikr_st['USER_ACTION_DATE'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ikr_st['USER_POSITION'] = user.point.region.name_ru + 'карантин'
            ikr_st['USER_INN'] = str(user.tin)
            ikr_st['ORGAN_ID'] = user.point.region.gtk_code
            ikr_st['ORGAN_NAME'] = user.point.region.name_ru + 'карантин'
            ikr_st['ORGAN_PHONE'] = user.point.region.phone

            integration = Integration.objects.filter(organization_code='GTK',
                                                     data_type=IntegratedDataType.IKR_STATUS).last()

            ikr_st['DOC_FNCT_CD'] = '019'
            ikr_st['PRICHINA'] = description
            IntegrationData.objects.create(
                integration=integration,
                data=status_json_data
            )

            IKRApplicationStatusStep.objects.create(
                application=ikr_application,
                status=ApplicationStatuses.ZERO_ONE_NINE,
                description=description,
                sender=user,
            )


def send_integrated_data():
    try:
        IntegrationData.send_integration_data()
    except Exception as e:
        print(e)

def seed_to_gtk():
    ikrs = IKR.all_objects.filter(application__isnull=True, number__startswith='2115', is_transit=False)
    for ikr in ikrs:
        user = ikr.owner
        importer_region_code = ''
        importer_region_name_ru = ''
        exporter_country_code = ''
        exporter_country_name_ru = ''
        point_region_code = ''
        point_region_name_ru = ''
        transit_exporter_country_code = ''
        transit_exporter_country_name_ru = ''
        transit_importer_country_code = ''
        transit_importer_country_name_ru = ''
        point_code = ''
        point_name_ru = ''
        entering_point_in_transit_code = ''
        leaving_point_in_transit_code = ''
        entering_point_in_transit_name_ru = ''
        leaving_point_in_transit_name_ru = ''
        expected_entering_date_in_transit = ''
        expected_leaving_date_in_transit = ''
        if ikr.importer_region:
            importer_region_code = ikr.importer_region.code
            importer_region_name_ru = ikr.importer_region.name_ru
        if ikr.exporter_country:
            exporter_country_code = ikr.exporter_country.code
            exporter_country_name_ru = ikr.exporter_country.name_ru
        if ikr.point:
            point_region_code = ikr.point.region.code
            point_region_name_ru = ikr.point.name_ru
            point_code = ikr.point.code
            point_name_ru = ikr.point.name_ru
        if ikr.transit_exporter_country:
            transit_exporter_country_code = ikr.transit_exporter_country.code
            transit_exporter_country_name_ru = ikr.transit_exporter_country.name_ru
        if ikr.transit_importer_country:
            transit_importer_country_code = ikr.transit_importer_country.code
            transit_importer_country_name_ru = ikr.transit_importer_country.name_ru
        if ikr.entering_point_in_transit:
            entering_point_in_transit_code = ikr.entering_point_in_transit.code
            entering_point_in_transit_name_ru = ikr.entering_point_in_transit.name_ru
        if ikr.leaving_point_in_transit:
            leaving_point_in_transit_code = ikr.leaving_point_in_transit.code
            leaving_point_in_transit_name_ru = ikr.leaving_point_in_transit.name_ru
        if ikr.expected_entering_date_in_transit:
            expected_entering_date_in_transit = ikr.expected_entering_date_in_transit.strftime("%Y-%m-%d")
        if ikr.expected_leaving_date_in_transit:
            expected_leaving_date_in_transit = ikr.expected_leaving_date_in_transit.strftime("%Y-%m-%d")

        locale.setlocale(locale.LC_ALL, 'ru_RU')  # to show months in russian messages
        number = ikr.number
        file_name = 'ikr_' + str(number)
        fs = FileSystemStorage()
        ikr_file = f'blanks/{file_name}.pdf'  # look up file from media automatically
        if not fs.exists(ikr_file):
            fs = FileSystemStorage()
            locale.setlocale(locale.LC_ALL, 'ru_RU')  # to show months in russian messages
            pdfmetrics.registerFont(TTFont('Verdana', 'Verdana.ttf'))
            number = ikr.number
            file_name = 'ikr_' + str(number)
            qrcode_link = f'blanks/qr_code/{file_name}.png'  # look up file from media automatically
            if fs.exists(qrcode_link):
                qrcode_image = ImageReader(f'media/blanks/qr_code/{file_name}.png')
            else:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=6,
                    border=0,
                )
                qr.add_data(f'https://efito.uz/check-certificate/?type=ikr&number={number}')
                qr.make(fit=True)
                img = qr.make_image()
                img.save(f'media/blanks/qr_code/{file_name}.png')
                qrcode_image = ImageReader(f'media/blanks/qr_code/{file_name}.png')

            first_packet = io.BytesIO()

            # create a new PDF with Reportlab
            first_page_one_context = canvas.Canvas(first_packet, pagesize=letter)
            if ikr.is_transit:
                first_page_one_context.setFont('Verdana', 12)
                first_page_one_context.drawString(5.5 * cm, 24.5 * cm, '(Транзит)')
            first_page_one_context.setFont('Verdana', 8)
            importer_name = ikr.importer_name
            importer_name_part_one = ''
            importer_name_part_two = ''
            importer_name_part_three = ''
            for importer_name in importer_name.split():
                if len(importer_name_part_one + importer_name) < 30 and len(importer_name_part_two) < 1:
                    importer_name_part_one = importer_name_part_one + ' ' + importer_name
                elif len(importer_name_part_two + importer_name) < 30 and len(importer_name_part_three) < 1:
                    importer_name_part_two = importer_name_part_two + ' ' + importer_name
                elif len(importer_name_part_three + importer_name) < 30:
                    importer_name_part_three = importer_name_part_three + ' ' + importer_name
            first_page_one_context.drawString(1.4 * cm, 21.6 * cm, importer_name_part_one)
            if importer_name_part_two:
                first_page_one_context.drawString(1.4 * cm, 21.2 * cm, importer_name_part_two)
            if importer_name_part_three:
                first_page_one_context.drawString(1.4 * cm, 20.8 * cm, importer_name_part_three)

            first_page_one_context.drawString(7 * cm, 21.8 * cm, str(ikr.exporter_country.name_ru))
            exporter_name = ikr.exporter_organization_name
            exporter_name_part_one = ''
            exporter_name_part_two = ''
            exporter_name_part_three = ''
            for exporter_name in exporter_name.split():
                if len(exporter_name_part_one + exporter_name) < 45 and len(exporter_name_part_two) < 1:
                    exporter_name_part_one = exporter_name_part_one + ' ' + exporter_name
                elif len(exporter_name_part_two + exporter_name) < 45 and len(exporter_name_part_three) < 1:
                    exporter_name_part_two = exporter_name_part_two + ' ' + exporter_name
                elif len(exporter_name_part_three + exporter_name) < 45:
                    exporter_name_part_three = exporter_name_part_three + ' ' + exporter_name
            first_page_one_context.drawString(6.8 * cm, 21.4 * cm, exporter_name_part_one)
            if exporter_name_part_two:
                first_page_one_context.drawString(6.8 * cm, 21 * cm, exporter_name_part_two)
            if exporter_name_part_three:
                first_page_one_context.drawString(6.8 * cm, 20.6 * cm, exporter_name_part_three)
            first_page_one_context.drawString(15.3 * cm, 23.3 * cm, '№ ' + ikr.number)
            first_page_one_context.drawString(15.3 * cm, 22.2 * cm, str(ikr.given_date.strftime('%d-%m-%Y')))
            first_page_one_context.drawString(15.3 * cm, 21.2 * cm, str(ikr.deadline.strftime('%d-%m-%Y')))

            products = ''
            counter = 0
            products_parts_list = []
            product_part = ''
            for product in ikr.products.all():
                counter = counter + 1
                products = f'{products} {counter}. {product.name}({product.hs_code.code})-{product.quantity} {product.unit.name_ru};'
            for product in products.split():
                if len(product_part + product) < 85:
                    product_part = product_part + product + ' '
                else:
                    products_parts_list.append(product_part)
                    product_part = ''
                    product_part = product + ' '
            if len(product_part) < 85:
                products_parts_list.append(product_part)  # do not remove this line never ever
            y = 18.8
            for products_part in products_parts_list:
                first_page_one_context.drawString(1.4 * cm, y * cm, products_part)
                y = y - 0.4

            first_page_one_context.drawString(16 * cm, 16.8 * cm, ikr.exporter_country.name_ru)
            route = ikr.route
            route_part_one = ''
            route_part_two = ''
            for route in route.split():
                if len(route_part_one + route) < 50 and len(route_part_two) < 1:
                    route_part_one = route_part_one + ' ' + route
                elif len(route_part_two + route) < 50:
                    route_part_two = route_part_two + ' ' + route
            first_page_one_context.drawString(1.4 * cm, 10.8 * cm, route_part_one)
            if route_part_two:
                first_page_one_context.drawString(1.4 * cm, 10.4 * cm, route_part_two)

            first_page_one_context.drawString(11 * cm, 10.4 * cm, ikr.point.name_ru)
            first_page_one_context.drawString(17 * cm, 10.4 * cm, ikr.get_transport_method_display())
            if ikr.request_and_contract_info:
                first_page_one_context.drawString(2 * cm, 8.2 * cm, ikr.request_and_contract_info)
            else:
                first_page_one_context.drawString(2 * cm, 8.2 * cm, 'контракт №' + ikr.request_number)

            extra_requirement = ikr.extra_requirement
            extra_requirement_part_one = ''
            extra_requirement_part_two = ''
            extra_requirement_part_three = ''
            extra_requirement_part_four = ''
            extra_requirement_part_five = ''
            for extra_requirement in extra_requirement.split():
                if len(extra_requirement_part_one + extra_requirement) < 90 and len(
                        extra_requirement_part_two) < 1:
                    extra_requirement_part_one = extra_requirement_part_one + ' ' + extra_requirement
                elif len(extra_requirement_part_two + extra_requirement) < 90 and len(
                        extra_requirement_part_three) < 1:
                    extra_requirement_part_two = extra_requirement_part_two + ' ' + extra_requirement
                elif len(extra_requirement_part_three + extra_requirement) < 90 and len(
                        extra_requirement_part_four) < 1:
                    extra_requirement_part_three = extra_requirement_part_three + ' ' + extra_requirement
                elif len(extra_requirement_part_four + extra_requirement) < 90 and len(
                        extra_requirement_part_five) < 1:
                    extra_requirement_part_four = extra_requirement_part_four + ' ' + extra_requirement
                elif len(extra_requirement_part_five + extra_requirement) < 90:
                    extra_requirement_part_five = extra_requirement_part_five + ' ' + extra_requirement

            first_page_one_context.drawString(4.5 * cm, 4.5 * cm, extra_requirement_part_one)
            if extra_requirement_part_two:
                first_page_one_context.drawString(4.5 * cm, 4.1 * cm, extra_requirement_part_two)
            if extra_requirement_part_three:
                first_page_one_context.drawString(4.5 * cm, 3.7 * cm, extra_requirement_part_three)
            if extra_requirement_part_four:
                first_page_one_context.drawString(4.5 * cm, 3.3 * cm, extra_requirement_part_four)
            if extra_requirement_part_five:
                first_page_one_context.drawString(4.5 * cm, 2.9 * cm, extra_requirement_part_five)

            first_page_one_context.drawImage(qrcode_image, 1.8 * cm, 2.95 * cm, width=55, height=55,
                                             mask='auto')
            if ikr.application:
                first_page_one_context.drawString(11.5 * cm, 2 * cm, 'Руководство')
            else:
                if ikr.owner:
                    first_page_one_context.drawString(11.5 * cm, 2 * cm, ikr.owner.name_ru)
                else:
                    first_page_one_context.drawString(11.5 * cm, 2 * cm, ikr.signatory)
            first_page_one_context.save()
            first_packet.seek(0)

            for_first_page = PdfFileReader(first_packet)

            second_packet = io.BytesIO()

            # create a new PDF with Reportlab
            second_page_one_context = canvas.Canvas(second_packet, pagesize=letter)
            second_page_one_context.setFont('Verdana', 8)

            related_pests = ''
            related_products = ''
            ikr_products = ikr.products
            products = ikr_products.order_by('hs_code').distinct('hs_code')
            counter = 0
            related_pests_parts_list = []
            related_pests_part = ''
            for product in products:
                counter = counter + 1
                related_pests_hs_codes = None
                related_products = ''
                for related_product in ikr_products.filter(hs_code=product.hs_code):
                    related_products = f'{related_products}{related_product.name}, '
                print('related_products')
                print(related_products)
                product_family = str(product.hs_code.code)
                product_family = product_family[:4]
                related_pests_hs_codes = PestHSCode.objects.filter(hs_code__contains=product_family)
                related_pests = related_pests + str(counter) + '. ' + related_products + ' - '
                for related_pests_hs_code in related_pests_hs_codes:
                    related_pests = f'{related_pests}, {related_pests_hs_code.pest}'
            for related_pest in related_pests.split():
                if len(related_pests_part + related_pest) < 110:
                    related_pests_part = related_pests_part + related_pest + ' '
                else:
                    related_pests_parts_list.append(related_pests_part)
                    related_pests_part = ''
                    related_pests_part = related_pest + ' '
            if len(related_pests_part) < 110:
                related_pests_parts_list.append(related_pests_part)  # do not remove this line never ever
            y = 25
            for related_pests_part in related_pests_parts_list:
                second_page_one_context.drawString(1.4 * cm, y * cm, related_pests_part)
                y = y - 0.4

            second_page_one_context.drawString(12 * cm, 3.2 * cm, '№ ' + ikr.number)
            second_page_one_context.drawString(15.3 * cm, 2.4 * cm, str(ikr.given_date.strftime('%d-%m-%Y')))
            second_page_one_context.drawString(16.2 * cm, 1.6 * cm, str(ikr.expire_date.strftime('%d-%m-%Y')))
            second_page_one_context.drawImage(qrcode_image, 2 * cm, 1.5 * cm, width=55, height=55, mask='auto')
            second_page_one_context.save()
            second_packet.seek(0)

            for_second_page = PdfFileReader(second_packet)
            ikr_pdf_template = PdfFileReader(open("static/blanks/ikr.pdf", "rb"))

            output = PdfFileWriter()

            first_page = ikr_pdf_template.getPage(0)
            first_page.mergePage(for_first_page.getPage(0))
            second_page = ikr_pdf_template.getPage(1)
            third_page = ikr_pdf_template.getPage(2)
            third_page.mergePage(for_second_page.getPage(0))
            output.addPage(first_page)
            output.addPage(second_page)
            output.addPage(third_page)

            output_stream = open("media/blanks/{}.pdf".format(file_name), "wb")
            output.write(output_stream)
            output_stream.close()

        with open("media/blanks/{}.pdf".format(file_name), 'rb') as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            base64_message = base64_encoded_data.decode('utf-8')

        if ikr.importer_type == 1:
            importer_type_code = '001'
            importer_type_name = CustomerType.dictionary[1]
        else:
            importer_type_code = '002'
            importer_type_name = CustomerType.dictionary[2]
        if ikr.applicant_type == 1:
            applicant_type_code = '001'
            applicant_type_name = CustomerType.dictionary[1]
        else:
            applicant_type_code = '002'
            applicant_type_name = CustomerType.dictionary[2]

        products_in_json = [{"CRPP_NO": str(ikr.number),  # must_be_unique
                             "CMDT_SRNO": str(index + 1),  # here for loop counter
                             "RQST_NO": ikr.request_number,  # must_be_unique
                             "HS_CD": product.hs_code.code,
                             "CMDT_NM": product.name,
                             "CMDT_QTY": format(product.quantity, '.3f'),
                             "CMDT_QTY_UT_CD": str(product.unit.code),
                             "CMDT_QTY_UT_NM": product.unit.name_ru,
                             "CMDT_TTWG": '',
                             "CMDT_TTWG_UT_CD": '',
                             "CMDT_TTWG_UT_NM": '',
                             "FRST_REGST_ID": ikr.applicant_tin,
                             "FRST_RGSR_DTL_DTTM": ikr.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                             "LAST_CHPR_ID": str(user.tin),
                             "LAST_CHNG_DTL_DTTM": ikr.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                             } for index, product in enumerate(ikr.products.all())]

        diseases_in_json = [{"QUAN_SRNO": '',
                             "CRPP_NO": '',
                             "RQST_NO": '',
                             "QUAN_BHI_CD": '',
                             "QUAN_BHI_NM": '',
                             "QUAN_BHI_CN": '',
                             "FRST_REGST_ID": '',
                             "FRST_RGSR_DTL_DTTM": '',
                             "LAST_CHPR_ID": '',
                             "LAST_CHNG_DTL_DTTM": '',
                             }]

        status_json_data = {
            "KR_Sert_Information": {"Information_Date": ikr.added_at.strftime("%Y-%m-%d %H:%M:%S"),
                                    "KR_Sert_asosiy": {
                                        "CRPP_NO": str(ikr.number),
                                        "RQST_NO": ikr.request_number,
                                        "DOC_NO": "ED-POT-RES-023",
                                        "DOC_NM": "Карантинное Разрешение",
                                        "DOC_FNCT_CD": "106",
                                        "CRPP_LNGA_TPCD": "RU",
                                        "CRPP_LNGA_TP_NM": "Русский язык",
                                        "RQST_DT": ikr.request_date.strftime("%Y-%m-%d"),
                                        "CRPP_PBLS_ITT_CD": '06.50',
                                        "CRPP_PBLS_ITT_NM": '06.50 - Уздавкарантин',
                                        "CRPP_PBLS_ITT_REGN_TPCD": '007',
                                        "CRPP_PBLS_ITT_REGN_TP_NM": 'г. Ташкент',
                                        "CRPP_PBLS_ITT_ADDR": 'ул. Бабур, 1-тупик, дом 17. 100100',
                                        "FMD_NO": str(ikr.number),
                                        "CRPP_VALT_PRID_STRT_DT": ikr.given_date.strftime("%Y-%m-%d"),
                                        "CRPP_VALT_PRID_XPIR_DT": ikr.expire_date.strftime("%Y-%m-%d"),
                                        "CRPP_PBLS_DT": ikr.given_date.strftime("%Y-%m-%d"),
                                        "IMEX_TPCD": "001",
                                        "IMEX_TP_NM": "Импорт",
                                        "APLC_TPCD": applicant_type_code,
                                        "APLC_TP_NM": applicant_type_name,
                                        "APLC_TXPR_UNIQ_NO": ikr.applicant_tin,
                                        "APLC_NM": ikr.applicant_name,
                                        "APLC_RPPN_NM": ikr.applicant_representative_name,
                                        "APLC_REGN_TPCD": ikr.applicant_region.code,
                                        "APLC_REGN_TP_NM": ikr.applicant_region.name_ru,
                                        "APLC_ADDR": ikr.applicant_address,
                                        "APLC_TELNO": ikr.applicant_phone,
                                        "APLC_FAX_NO": ikr.applicant_fax,
                                        "APLC_RETL_WRPR_RGSR_NO": '',
                                        "APLC_RETL_WRPR_PBLS_DT": '',
                                        "IMPPN_TPCD": importer_type_code,
                                        "IMPPN_TP_NM": importer_type_name,
                                        "IMPPN_TXPR_UNIQ_NO": str(ikr.importer_tin),
                                        "IMPPN_NM": ikr.importer_name,
                                        "IMPPN_RPPN_NM": ikr.importer_representative_name,
                                        "IMPPN_REGN_TPCD": importer_region_code,
                                        "IMPPN_REGN_TP_NM": importer_region_name_ru,
                                        "IMPPN_ADDR": ikr.importer_address,
                                        "IMPPN_TELNO": ikr.importer_phone_number,
                                        "IMPPN_FAX_NO": ikr.importer_fax,
                                        "IMPPN_RETL_WRPR_RGSR_NO": '',
                                        "IMPPN_RETL_WRPR_PBLS_DT": '',
                                        "EXPPN_NM": ikr.exporter_organization_name,
                                        "EXCY_CD": exporter_country_code,
                                        "EXCY_NM": exporter_country_name_ru,
                                        "EXPPN_ADDR": ikr.exporter_address,
                                        "ARLC_REGN_TPCD": point_region_code,
                                        "ARLC_REGN_TP_NM": point_region_name_ru,
                                        "ARLC_ADDR": '',
                                        "DPTR_THRG_CNTY_CD": transit_exporter_country_code,
                                        "DPTR_THRG_CNTY_NM": transit_exporter_country_name_ru,
                                        "ARVL_THRG_CNTY_CD": transit_importer_country_code,
                                        "ARVL_THRG_CNTY_NM": transit_importer_country_name_ru,
                                        "TRNP_METH_CD_1": "0" + str(ikr.transport_method),
                                        "TRNP_METH_NM_1": TransPortTypes.gtk_dictionary[ikr.transport_method],
                                        "TRNP_METH_CD_2": '',
                                        "TRNP_METH_NM_2": '',
                                        "TRNP_PATH_CN": ikr.route,
                                        "ARLC_NM": point_code + ' ' + point_name_ru,
                                        "QUAN_PCDR_CN": '',
                                        "ADIT_REQS_MATR_CN": ikr.extra_requirement,
                                        "WRPR_PBLS_BSS_CN": ikr.request_and_contract_info,
                                        "APVR_ID": '',
                                        "APVR_NM": ikr.owner.name_ru,
                                        "APRE_YN": "Y",
                                        "IMCY_CD": "",
                                        "IMCY_NM": "",
                                        "IN_BORDER_CUSTOMS_OFFICE_CD": entering_point_in_transit_code,
                                        "OUT_BORDER_CUSTOMS_OFFICE_CD": leaving_point_in_transit_code,
                                        "IN_BORDER_CUSTOMS_OFFICE_NM": entering_point_in_transit_name_ru,
                                        "OUT_BORDER_CUSTOMS_OFFICE_NM": leaving_point_in_transit_name_ru,
                                        "PLNT_EXPECTED_TRANSIT_START_DT": expected_entering_date_in_transit,
                                        "PLNT_EXPECTED_TRANSIT_END_DT": expected_leaving_date_in_transit,
                                        "FOR_TRANSIT_YN": "Y" if ikr.is_transit else '',
                                        "RENEWAL_CRPP_VALT_PRID_XPIR_DT": '',
                                        "RENEWAL_APRE_YN": '',
                                        "RENEWAL_RQST_NO": '',
                                        "STRZT_PRCS_ESNT_YN": '',
                                        "CERTIFICATE_FILE_EXT": "pdf",
                                        "CERTIFICATE_FILE": base64_message,
                                        "PRICHINA": "Одобрение",
                                        "USER_FULL_NAME": user.name_ru,
                                        "USER_PHONE": user.phone,
                                        "USER_ACTION_DATE": ikr.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                                        "USER_POSITION": user.point.region.name_ru + "карантин",
                                        "USER_INN": str(user.tin),
                                        "ORGAN_ID": user.point.region.gtk_code,
                                        "ORGAN_NAME": user.point.region.name_ru + "карантин",
                                        "ORGAN_PHONE": user.point.region.phone,
                                        "FRST_REGST_ID": ikr.applicant_tin,
                                        "FRST_RGSR_DTL_DTTM": '',
                                        "LAST_CHPR_ID": str(user.tin),
                                        "LAST_CHNG_DTL_DTTM": ikr.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                                        "QUAN_BHI_CD": '',
                                        "QUAN_BHI_NM": '',
                                        "QUAN_BHI_CN": '',
                                        "Tovar": products_in_json,
                                    }
                                    }
        }
        integration = Integration.objects.filter(organization_code='GTK',
                                                 data_type=IntegratedDataType.IKR).last()
        IntegrationData.objects.create(
            integration=integration,
            data=status_json_data
        )
        print(ikr.request_number)
    else:
        print('Попробуйте снова')


def change_akd():
    akds = AKD.objects.filter(given_date__gte='2022-01-01')
    for akd in akds:
        akd.is_synchronised = False
        akd.save()


def download_balance_in_excel():
    response = HttpResponse(content_type='application/ms-excel')

    # decide file name
    file_name = 'balances'
    response['Content-Disposition'] = f'attachment; filename="{file_name}.xls"'

    # creating workbook
    wb = xlwt.Workbook(encoding='utf-8')

    # adding sheet
    ws = wb.add_sheet("sheet1")

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    # headers are bold
    font_style.font.bold = True

    # column header names, you can use your own headers here
    columns = ['Organization', 'TIN', 'SERVICE TYPE', 'Balance', 'Date', 'Inspection']

    # write column headers in sheet
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    balances = Balance.objects.filter(month='2022-01-01')
    for balance in balances:
        row_num = row_num + 1
        ws.write(row_num, 1, balance.organization.name, font_style)
        ws.write(row_num, 2, balance.organization.tin, font_style)
        ws.write(row_num, 3, balance.get_service_type_display(), font_style)
        ws.write(row_num, 4, balance.amount, font_style)
        ws.write(row_num, 5, '01-01-2021', font_style)
        ws.write(row_num, 6, balance.region.name_ru, font_style)

    print('test')
    wb.save(response)
    return response


def logout_all_users():
    all_sessions = Session.objects.all()
    for session in all_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id'):
            session.delete()


def akds_control():
    protocols = ImportProtocol.objects.filter(added_at__gte='2021-05-01')

    for protocol in protocols:
        protocol_added_at = protocol.added_at
        protocol_conclusion = protocol.conclusion
        tbotds = protocol.shortcut.tbotds.all()
        for tbotd in tbotds:
            try:
                akd = tbotd.akd
                print('akd')
                print(akd.number)
                days_ago = (akd.added_at - protocol_added_at).total_seconds() / 86400
                if days_ago > 3:
                    print('days_ago')
                    print(days_ago)
            except Exception as e:
                print(str(e))
    # akds = AKD.objects.filter(tbotd__ikr_shipment__status=IKRShipmentStatuses.READY_FOR_AKD)
    # count = 0
    # for akd in akds:
    #     count = count + 1
    #
    #     ikr_shipment = akd.tbotd.ikr_shipment
    #     ikr_shipment.status = IKRShipmentStatuses.APPROVED
    #     ikr_shipment.save()
    #     print(f'{count}. {akd.number}')


def import_protocol_inspection_generals():
    import_protocols = ImportProtocol.objects.all()
    for import_protocol in import_protocols:
        shortcut = import_protocol.shortcut
        if len(str(shortcut.ikr.point.region.pk)) == 1:
            inspection_code = '0' + str(shortcut.ikr.point.region.pk) + '000'
        else:
            inspection_code = str(shortcut.ikr.point.region.pk) + '000'
        try:
            inspection_general = User.objects.get(point__code=inspection_code, username__startswith='g')
        except User.DoesNotExist:
            inspection_general = User.objects.get(username='admin')
        import_protocol.inspection_general = inspection_general
        import_protocol.save()


def seed_import_protocol_payment_amount():
    col_names = ('number', 'payment_amount')
    lab_protocols_price = pd.read_csv("static/database_files/lab_protocols_payment_amount.csv", sep=",", names=col_names, header=None)
    for index, lab_protocol_price in lab_protocols_price.iterrows():
        try:
            import_protocol = ImportProtocol.objects.get(number=lab_protocol_price.number)
            import_protocol.payment_amount = float(lab_protocol_price.payment_amount)
            import_protocol.save()
            print(f'{lab_protocol_price.number} has been added successfully')
        except Exception as e:
            print(f'#{lab_protocol_price.number}. Errors: {e}')


def seed_chemical_reactives():
    col_names = ('name_ru', 'unit')
    chemical_reactives = pd.read_csv("static/database_files/chemical_reactives.csv", sep=",", names=col_names, header=None)
    for index, chemical_reactive in chemical_reactives.iterrows():
        _, is_new = LabChemicalReactive.objects.get_or_create(
            name=chemical_reactive.name_ru,
            unit_id=int(chemical_reactive.unit),
        )
        if is_new:
            print(f'{chemical_reactive.name_ru} has been added successfully')
        else:
            print(f'{chemical_reactive.name_ru} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_disposables():
    col_names = ('name_ru', 'unit')
    disposables = pd.read_csv("static/database_files/disposables.csv", sep=",", names=col_names, header=None)
    for index, disposable in disposables.iterrows():
        _, is_new = LabDisposable.objects.get_or_create(
            name=disposable.name_ru,
            unit_id=int(disposable.unit),
        )
        if is_new:
            print(f'{disposable.name_ru} has been added successfully')
        else:
            print(f'{disposable.unit} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def seed_lab_test_methods():
    col_names = ('namee', 'normative_document', 'expertise_type', 'accreditation_type')
    lab_test_methods = pd.read_csv("static/database_files/lab_test_method.csv", sep=",", names=col_names, header=None)
    for index, lab_test_method in lab_test_methods.iterrows():
        _, is_new = LabTestMethod.objects.get_or_create(
            name=lab_test_method.namee,
            normative_document=lab_test_method.normative_document,
            expertise_type=lab_test_method.expertise_type,
            accreditation_type=lab_test_method.accreditation_type,
        )
        if is_new:
            print(f'{lab_test_method.namee} has been added successfully')
        else:
            print(f'{lab_test_method.namee} could not be added, any error occurred or it is already exist!!!!!!!!!!!')


def reject_delayed_applications():
    applications = IKRApplication.objects.filter(is_active=False).exclude(
        status__in=[ApplicationStatuses.ZERO_ONE_NINE, ApplicationStatuses.ONE_ZERO_SIX])
    user = User.objects.get(username='a201283204')
    integration = Integration.objects.filter(organization_code='GTK',
                                             data_type=IntegratedDataType.IKR_STATUS).last()

    status_json_data = {"KR_ST_Information": {"Information_Date": "",
                                              "KR_ST": {
                                                  "RQST_NO": "",
                                                  "RQST_DT": "",
                                                  "DOC_FNCT_CD": "",
                                                  "PRICHINA": "",
                                                  "USER_FULL_NAME": "",
                                                  "USER_PHONE": "",
                                                  "USER_ACTION_DATE": "",
                                                  "USER_POSITION": "",
                                                  "USER_INN": "",
                                                  "ORGAN_ID": "",
                                                  "ORGAN_NAME": "",
                                                  "ORGAN_PHONE": ""
                                              }
                                              }
                        }
    status_json_data['KR_ST_Information']['Information_Date'] = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S")
    ikr_st = status_json_data['KR_ST_Information']['KR_ST']
    ikr_st['USER_FULL_NAME'] = user.name_ru
    ikr_st['USER_PHONE'] = user.phone
    ikr_st['USER_ACTION_DATE'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ikr_st['USER_POSITION'] = user.point.region.name_ru + 'карантин'
    ikr_st['USER_INN'] = str(user.tin)
    ikr_st['ORGAN_ID'] = user.point.region.gtk_code
    ikr_st['ORGAN_NAME'] = user.point.region.name_ru + 'карантин'
    ikr_st['ORGAN_PHONE'] = user.point.region.phone
    for application in applications:
        seconds_ago = (datetime.datetime.now() - application.added_at).total_seconds()
        if seconds_ago > 3600 * 24 * 9:
            ikr_st['RQST_NO'] = application.request_number
            ikr_st['RQST_DT'] = application.request_date.strftime("%Y-%m-%d")
            ikr_st[
                'PRICHINA'] = 'Ўрнатилган тартибда кўриб чиқиш муддати тугаганлиги сабабли аризангиз қайтарилди. Илтимос, аризани қайтадан киритинг. Заявка отклонена по причине истечения установленного срока рассмотрения. Просим подать заявку заново.'
            ikr_st['DOC_FNCT_CD'] = '019'
            IntegrationData.objects.create(
                integration=integration,
                data=status_json_data
            )
            application.status = ApplicationStatuses.ZERO_ONE_NINE
            application.is_active = False
            application.is_paid = False
            application.save()
            IKRApplicationStatusStep.objects.create(
                application=application,
                status=ApplicationStatuses.ZERO_ONE_NINE,
                description=ikr_st['PRICHINA'],
                sender=user,
            )
            print('Request number: ' + str(application.request_number) + ' <=> ' + str(application.request_date.strftime("%Y-%m-%d")))


def add_recvisits_to_invoices():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    invoices = Invoice.active_objects.all()

    for invoice in invoices:
        print(invoice.number)
        organization_bank_name = None

        profile_response = requests.get(
            os.environ.get('DIDOX_API_BASE_URL') + f'/v1/profile/{invoice.applicant_tin}?document_date=',
            proxies=proxy_config,
            headers={'api-key': cache.get('didox_signed_in_token'),
                     'user-key': cache.get('didox_signed_in_token'),
                     'Content-Type': 'application/json'},
            verify=False)

        banks_response = requests.get('https://stage.goodsign.biz/v1/banks/all', proxies=proxy_config, verify=False)
        if profile_response.status_code == 200 and banks_response.status_code == 200:
            profile = profile_response.json()
            try:
                inspection_general = User.objects.filter(point__region=invoice.region,
                                                         username__startswith='g').last().name_ru.split()
                inspection_general = str(inspection_general[1][0] + '.' + inspection_general[0])
                organization_bank_name = \
                    list(filter(lambda item: item['bankId'] == profile.get('bankId'), banks_response.json()))[0]['name']
                invoice.applicant_organization = profile.get('name')
                invoice.organization_type = OrganizationType.BUDGET if profile.get(
                    'isBudget') == OrganizationType.BUDGET else OrganizationType.OTHERS
                invoice.inspection_general = inspection_general
                invoice.organization_bank_id = profile.get('bankId')
                invoice.organization_bank_name = organization_bank_name
                invoice.organization_bank_account = profile.get('account')
                invoice.organization_mfo = profile.get('mfo')
                invoice.organization_oked = profile.get('oked')
                invoice.organization_director = profile.get('director')
                invoice.organization_accountant = profile.get('accountant')
                invoice.organization_address = profile.get('address')
                invoice.save()
                print('Changed successfully.')
            except Exception as e:
                print(f'add_recvisits_to_invoices: {e}')


def loaddata():
    call_command('loaddata', 'myapp')