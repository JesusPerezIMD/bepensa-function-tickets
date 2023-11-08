import logging
import azure.functions as func
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    url = req.params.get('url')
    if not url:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            url = req_body.get('url')

    if url:
        result = analizar_ticket(url)
        json_result = json.dumps(result)
        return func.HttpResponse(json_result, mimetype="application/json")
    else:
        return func.HttpResponse(
            "Please pass a url on the query string or in the request body",
            status_code=400
        )

def analizar_ticket(url):
    endpoint = "https://citcognitiveservicedev.cognitiveservices.azure.com"
    key = "586bf736a33a4b8b8795ddd9d4aeb2e7"

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-receipt", url)
    receipts = poller.result()

    tipo_registro_map = {
        "receipt.retailMeal": "Comida",
        "receipt.creditCard": "Varios",
        "receipt.gas": "Transporte",
        "receipt.parking": "Varios",
        "receipt.hotel": "Hospedaje"
    }

    output = []
    for idx, receipt in enumerate(receipts.documents):
        # Obtener el objeto AddressValue si está disponible.
        merchant_address_value = receipt.fields.get("MerchantAddress").value if receipt.fields.get("MerchantAddress") else None
        
        if merchant_address_value:
            # Utilizar los campos de AddressValue para construir la dirección.
            address_components = [
                merchant_address_value.house_number,
                merchant_address_value.road,
                merchant_address_value.city,
                merchant_address_value.state,
                merchant_address_value.postal_code,
                merchant_address_value.country_region,
                merchant_address_value.street_address,
            ]
            # Filtrar los componentes que son None o vacíos.
            full_address = " ".join(filter(None, address_components))
            merchant_address_confidence = f"{receipt.fields.get('MerchantAddress').confidence * 100:.1f}%"
            merchant_address_line = f"{full_address}, Confianza: {merchant_address_confidence}"
        else:
            merchant_address_line = None

        tipo_registro = tipo_registro_map.get(receipt.doc_type, receipt.doc_type)
        merchant_name = receipt.fields.get("MerchantName").value if receipt.fields.get("MerchantName") else None
        merchant_name_confidence = f"{receipt.fields.get('MerchantName').confidence * 100:.1f}%" if merchant_name else None
        total_value = receipt.fields.get("Total").value if receipt.fields.get("Total") else None
        total_confidence = f"{receipt.fields.get('Total').confidence * 100:.1f}%" if total_value else None

        receipt_info = {
            "TipoRegistro": tipo_registro,
            "NombreComerciante": f"{merchant_name}, Confianza: {merchant_name_confidence}" if merchant_name else None,
            "LugarComerciante": merchant_address_line,
            "Importe": f"{total_value}, Confianza: {total_confidence}" if total_value else None,
            "Descripcion": "",
        }

        # Eliminar las claves con valores None antes de añadir al resultado final
        receipt_info = {k: v for k, v in receipt_info.items() if v is not None}
        output.append(receipt_info)

    return output



