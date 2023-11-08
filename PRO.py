import logging
import azure.functions as func
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
        return func.HttpResponse(result, mimetype="text/plain")
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

    output = ""
    for idx, receipt in enumerate(receipts.documents):
        output += "--------Reconociendo Recibo #{}--------\n".format(idx + 1)
        receipt_type = receipt.doc_type
        if receipt_type:
            output += "Tipo de recibo: {}\n".format(receipt_type)
        merchant_name = receipt.fields.get("MerchantName")
        if merchant_name:
            output += "Nombre del comerciante: {} con int. de confianza: {}\n".format(
                merchant_name.value, merchant_name.confidence
            )
        transaction_date = receipt.fields.get("TransactionDate")
        if transaction_date:
            output += "Fecha de emisión del recibo: {} con confianza: {}\n".format(
                transaction_date.value, transaction_date.confidence
            )
        if receipt.fields.get("Items"):
            output += "Artículos:\n"
            for idx, item in enumerate(receipt.fields.get("Items").value):
                output += "...Artículo #{}\n".format(idx + 1)
                item_description = item.value.get("Description")
                if item_description:
                    output += "......Descripción: {} con confianza: {}\n".format(
                        item_description.value, item_description.confidence
                    )
                item_quantity = item.value.get("Quantity")
                if item_quantity:
                    output += "......Cantidad: {} con confianza: {}\n".format(
                        item_quantity.value, item_quantity.confidence
                    )
                item_price = item.value.get("Price")
                if item_price:
                    output += "......Precio individual: ${} con confianza: {}\n".format(
                        item_price.value, item_price.confidence
                    )
                item_total_price = item.value.get("TotalPrice")
                if item_total_price:
                    output += "......Precio total: ${} con confianza: {}\n".format(
                        item_total_price.value, item_total_price.confidence
                    )
        subtotal = receipt.fields.get("Subtotal")
        if subtotal:
            output += "Subtotal: {} con confianza: {}\n".format(
                subtotal.value, subtotal.confidence
            )
        tax = receipt.fields.get("TotalTax")
        if tax:
            output += "Impuestos: ${} con confianza {}\n".format(tax.value, tax.confidence)
        tip = receipt.fields.get("Tip")
        if tip:
            output += "Propina: ${} con confianza: {}\n".format(tip.value, tip.confidence)
        total = receipt.fields.get("Total")
        if total:
            output += "Total: ${} con confianza: {}\n".format(total.value, total.confidence)
        output += "--------------------------------------\n"

    return output
