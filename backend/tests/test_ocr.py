def test_ocr_service_init():
    from app.reports.ai.ocr import OCRService
    service = OCRService()
    assert service is not None


def test_ocr_requires_ocr():
    from app.reports.ai.ocr import OCRService
    service = OCRService()
    assert service.requires_ocr("report.pdf", "pdf") is True
    assert service.requires_ocr("report.txt", "txt") is False
