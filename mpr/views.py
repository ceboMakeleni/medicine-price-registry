import json
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.conf import settings
import names

from mpr import models
import serialisers
import logging

logger = logging.getLogger(__name__)

def log_analytics(request, event, properties):
    try:
        import analytics
        from ipware.ip import get_ip as get_ip

        if settings.DEBUG: return
        if not hasattr(settings, "SEGMENT_IO_KEY"):
            logger.warning("Cannot send analytics. No Segment IO Key has been set")
            return

        if "pingdom" in request.META.get("HTTP_USER_AGENT", ""):
            logger.warning("Not recording analytics. Ignored pingdom bot")
            return

        api_key = settings.SEGMENT_IO_KEY

        ip = get_ip(request)

        name = names.get_full_name()
        uid = request.session.get("uid", name)
        request.session["uid"] = uid
        analytics.init(api_key)
        analytics.identify(uid,
            {
                "$name" : uid,
            },
            { "$ip" : ip}
        )
        analytics.track(uid, event=event, properties=properties)
    except Exception, e:
        logger.exception("Error handling analytics")
    

def search_by_ingredient(request):
    q = request.GET.get("q", "").strip()

    if len(q) < 3:
        products = []
    else:
        products = models.Product.objects.search_by_ingredient(q)
        products = serialisers.serialize_products(products)
    return HttpResponse(
        json.dumps(products, indent=4), mimetype="application/json"
    )

def search_by_product(request):
    q = request.GET.get("q", "").strip()

    if len(q) < 3:
        products = []
    else:
        products = models.Product.objects.search_by_product(q)
        products = serialisers.serialize_products(products)
    return HttpResponse(
        json.dumps(products, indent=4), mimetype="application/json"
    )

def search(request, serialiser=serialisers.serialize_products):
    q = request.GET.get("q", "").strip()

    log_analytics(request, "#search", {
        "search_string" : q
    })

    all_products = set()
    if len(q) < 3:
        products = []
    else:
        products1 = set(models.Product.objects.search_by_product(q))
        products2 = set(models.Product.objects.search_by_ingredient(q))
        all_products |= products1 | products2
        all_products = sorted(all_products, key=lambda x: x.sep)
        products = serialiser(all_products)
    return HttpResponse(
        json.dumps(products, indent=4), mimetype="application/json"
    )

def search_lite(request):
    return search(request, serialisers.serialize_products_lite)

def related_products(request):
    product_id = request.GET.get("product", "").strip()
    product = get_object_or_404(models.Product, id=product_id)
    log_analytics(request, "#related", product_properties(product))

    return HttpResponse(
        json.dumps(
            serialisers.serialize_products(product.related_products), indent=4
        ), mimetype="application/json"
    )
    
def product_properties(product):
    return {
        "product" : product.name,
        "product_id" : product.id,
        "dosage_form" : product.dosage_form,
        "is_generic" : product.is_generic
    }

def product_detail(request):
    product_id = request.GET.get("product", "").strip()
    product = get_object_or_404(models.Product, id=product_id)

    log_analytics(request, "#product-detail", product_properties(product))

    return HttpResponse(
        json.dumps(
            serialisers.serialize_product(product), indent=4
        ), mimetype="application/json"
    )

def dump(request):
    log_analytics(request, "#dump", {})


    return HttpResponse(
        json.dumps(
            serialisers.serialize_products(models.Product.objects.all()), indent=4
        ), mimetype="application/json"
    )
