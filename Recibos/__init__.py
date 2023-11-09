import logging
import json
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Asegúrate de que la solicitud es una solicitud POST
        if req.method != 'POST':
            return func.HttpResponse(
                "This endpoint only supports POST requests.",
                status_code=405
            )

        # Leer el archivo de la imagen desde los datos del formulario 'form-data'
        file = req.files.get('file')
        if not file:
            return func.HttpResponse(
                "Please upload the file with the 'file' key in form-data.",
                status_code=400
            )
        image_bytes = file.read()

        # Procesar la imagen y obtener el resultado
        result = analizar_ticket(image_bytes)
        json_result = json.dumps(result)

        # Imprimir el resultado en la consola para propósitos de depuración
        logging.info(f'Resultado del análisis de la imagen: {json_result}')

        return func.HttpResponse(json_result, mimetype="application/json")
    except ValueError as ve:
        return func.HttpResponse(
            f"Error reading image file: {str(ve)}",
            status_code=400
        )

def analizar_ticket(image_bytes):
    endpoint = "https://citcognitiveservicedev.cognitiveservices.azure.com"
    key = "586bf736a33a4b8b8795ddd9d4aeb2e7"

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document("prebuilt-receipt", image_bytes)
    receipts = poller.result()

    tipo_registro_map = {
        "receipt.retailMeal": "Comida",
        "receipt.creditCard": "Varios",
        "receipt.gas": "Transporte",
        "receipt.parking": "Varios",
        "receipt.hotel": "Hospedaje"
    }

    output = []
    for receipt in receipts.documents:
        fields = {
            "MerchantName": receipt.fields.get("MerchantName"),
            "MerchantAddress": receipt.fields.get("MerchantAddress"),
            "Total": receipt.fields.get("Total")
        }

        confident_fields = {
            key: value for key, value in fields.items() if value and value.confidence >= 0.5
        }

        merchant_address_line = ""
        if "MerchantAddress" in confident_fields:
            merchant_address_value = confident_fields["MerchantAddress"].value
            address_components = [
                merchant_address_value.house_number,
                merchant_address_value.road,
                merchant_address_value.city,
                merchant_address_value.state,
                merchant_address_value.postal_code,
                merchant_address_value.country_region,
                merchant_address_value.street_address,
            ]
            full_address = " ".join(filter(None, address_components))
            merchant_address_line = full_address

        tipo_registro = tipo_registro_map.get(receipt.doc_type, "Otro")

        receipt_info = {
            "TipoRegistro": tipo_registro,
            "NombreComerciante": confident_fields['MerchantName'].value if "MerchantName" in confident_fields else "",
            "LugarComerciante": merchant_address_line,
            "Importe": confident_fields['Total'].value if "Total" in confident_fields else "",
            "Descripcion": "",
        }

        output.append(receipt_info)

    return output
