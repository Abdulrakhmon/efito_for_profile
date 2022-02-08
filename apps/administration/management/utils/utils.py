# import tempfile
#
import tempfile

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
#
#
def render_to_pdf(request,template_src, context):
    html_string = render_to_string(template_src,{'akd':context})
    html = HTML(string=html_string,base_url=request.build_absolute_uri())
    result = html.write_pdf()

    # Creating http response
    response = HttpResponse(content_type='application/pdf;')
    response['Content-Disposition'] = f'inline; filename={context.number}.pdf'
    response['Content-Transfer-Encoding'] = 'binary'
    with tempfile.NamedTemporaryFile(delete=True) as output:
        output.write(result)
        output.flush()
        output = open(output.name, 'rb')
        response.write(output.read())

    return response
