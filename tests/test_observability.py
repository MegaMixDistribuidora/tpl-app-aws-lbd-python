from service_template.observability import logger, metrics, tracer


def test_logger_has_the_service_name():
    assert logger.service == "service-template"


def test_metrics_has_the_namespace_and_service():
    assert metrics.namespace == "MegaMix"
    assert metrics.service == "service-template"


def test_tracer_has_the_service_name():
    assert tracer.service == "service-template"
