from decimal import Decimal


class WithholdingService:
    @staticmethod
    def calculate(receipt_header):
        """
        Calculates withholding amount based on:
          - expense category
          - goods > 10,000 ETB → 2%
          - services > 3,000 ETB → 2%
        """
        financial_info = receipt_header.financial_info

        if not financial_info.withholding_applicable or financial_info.category != 'expense':
            return Decimal('0.00')

        items = receipt_header.items.all()
        total_withholding = Decimal('0.00')

        for item in items:
            if item.item_type == 'goods' and financial_info.subtotal > Decimal('10000'):
                total_withholding += item.raw_total_amount_before_tax * Decimal('0.02')
            elif item.item_type == 'service' and financial_info.subtotal > Decimal('3000'):
                total_withholding += item.raw_total_amount_before_tax * Decimal('0.02')

        return total_withholding.quantize(Decimal('0.01'))
