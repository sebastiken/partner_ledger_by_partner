##############################################################################
# COPYRIGHT
##############################################################################

from report import report_sxw
from report.report_sxw import rml_parse
import random
from datetime import datetime
from operator import itemgetter

LINES_PER_PAGE = 21

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_invoices': self.get_invoices,
            'get_lines': self.get_lines,
            'get_advanced_payments': self.get_advanced_payments,
            'get_nc_not_applied': self.get_nc_not_applied,
            'get_total_due': self.get_total_due,
            'get_invoice_residual': self.get_invoice_residual,
            #'total_debit': self.get_total_debit,
            #'total_credit': self.get_total_credit,
            #'total_saldo': self.get_total_saldo,
        })
        self.total_due = 0.0
        self._invoice_residual = {}

    def set_context(self, objects, data, ids, report_type=None):
        super(Parser, self).set_context(objects, data, ids, report_type)

    def get_invoices(self, partner):
        inv_obj = self.pool.get('account.invoice')
        
        invoice_ids = inv_obj.search(self.cr, self.uid, [('partner_id', '=', partner.id), ('documento', 'in', ['factura', 'nota_debito'])], order='date_invoice asc')
        invoices = inv_obj.browse(self.cr, self.uid, invoice_ids)
        for inv in invoices:
            self._invoice_residual[inv.id] = inv.amount_total
        return invoices

    def get_lines(self, invoice):
        move_lines = []
        print '*****************************'
        print 'INVOICE: ', invoice.number, invoice.move_lines
        for l in invoice.move_lines:
            print 'ID: %d Name: %s reconciled: %s [%s] debit: %f credit: %f' % (l.id, l.name, l.reconcile_id.name, l.reconcile_partial_id.name, l.debit, l.credit)
            m = {}
            if l.name.startswith('Currency') and l.credit != 0:
                continue
            m['name'] = l.ref and l.ref+l.name or l.name
            m['date'] = l.date_created
            m['credit'] = l.credit or -l.debit
            move_lines.append(m)
            self._invoice_residual[invoice.id] -= m['credit']

        return move_lines

    def get_advanced_payments(self, partner):
        adv_obj = self.pool.get('payment.advanced.pay')  
        adv_ids = adv_obj.search(self.cr, self.uid, [('partner_id', '=', partner.id), ('state', 'in', ['draft', 'open'])])
        adv_pays = adv_obj.browse(self.cr, self.uid, adv_ids)

        print '1: ', self.total_due
        for adv in adv_pays:
            self.total_due -= adv.remainder
        print '2: ', self.total_due
        return adv_pays

    def get_nc_not_applied(self, partner):
        inv_obj = self.pool.get('account.invoice')  

        credit_note_ids = inv_obj.search(self.cr, self.uid, [('partner_id', '=', partner.id), ('documento', 'in', ['nota_credito']), ('name', '=', False)], order='date_invoice desc')
        credit_notes =  inv_obj.browse(self.cr, self.uid, credit_note_ids)

        print '3: ', self.total_due
        for nc in credit_notes:
            self.total_due -= nc.amount_total
        print '4: ', self.total_due

        return credit_notes

    def get_total_due(self):
        print '5: ', self.total_due
        for k, v in self._invoice_residual.iteritems():
            self.total_due += v
            print '6: ', v, self.total_due
        return self.total_due

    def get_invoice_residual(self, invoice_id):
        #self.total_due += self._invoice_residual[invoice_id]
        #print 'Total Due: ', self._invoice_residual[invoice_id], self.total_due
        return round(self._invoice_residual[invoice_id], 2)
