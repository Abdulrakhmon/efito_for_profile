# from exim.models import IKR
# from administration.statuses import IKRShipmentStatuses
# from django.db.models import Q
#
#
# def ikr_template_variables(request):
#     user = request.user
#     if user.is_authenticated:
#         return {'pending_shipments_count': IKR.objects.filter(Q(point_id=request.user.point) |
#                                                               Q(point=None),
#                                                               shipments__status__in=[
#                                                                   IKRShipmentStatuses.COMING,
#                                                                   IKRShipmentStatuses.ARRIVED,
#                                                                   IKRShipmentStatuses.LATE,
#                                                                   IKRShipmentStatuses.LAB,
#                                                                   IKRShipmentStatuses.FUMIGATION]).count()}
#     else:
#         return {}
