import json
import os

from utils.logger import get_logger, MetricsLogger

logger = get_logger("price-tracker-scraper")
metrics = MetricsLogger(logger)

def lambda_handler(event, context):
    """Basic Lambda handler for testing deployment"""
    logger.info("Price tracker scraper started")
    logger.info(f"Event: {json.dumps(event)}")

    metrics.record("execution_id", context.aws_request_id)
    metrics.record("function_name", context.function_name)
    metrics.increment("executions")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Price tracker scraper executed successfully',
            'timestamp': context.aws_request_id
        })
    }