"""A small source-code example. FlowScope never runs this code."""
class PaymentService:
    def process(self, order, retries=3):
        if not order or not order.get('items'):
            return 'invalid'
        for attempt in range(retries):
            if order.get('authorized'):
                if order.get('stock'):
                    return 'accepted'
                return 'out of stock'
        return 'declined'

    def total(self, items):
        return sum(item['price'] for item in items if item['active'])
