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
            'get_moves':self.get_moves,
            'hello':self.hello_world,
            'total_debit': self.get_total_debit,
            'total_credit': self.get_total_credit,
            'total_saldo': self.get_total_saldo,
        })
        #self.inv_code = '0'

    def set_context(self, objects, data, ids, report_type=None):
        #print 'Data: ', data
        #print 'Objects: ', objects
        #print 'Ids: ', ids
        super(Parser, self).set_context(objects, data, ids, report_type)

#    def get_moves(self, partner):
#        full_moves = []
#
#        # SQL Query que nos entrega toda la informacion incluido
#        # informacion del objeto account_invoice
#        self.cr.execute("SELECT res.*, res.ref, inv.id, inv.number from account_invoice inv RIGHT JOIN " \
#        "(SELECT l.id, l.move_id, l.date,j.code, l.ref as ref, l.name, l.debit, l.credit " \
#            "FROM account_move_line l " \
#            "LEFT JOIN account_journal j " \
#            "ON (l.journal_id = j.id) " \
#            "WHERE l.partner_id = %s " \
#            "AND l.account_id IN (select id from account_account where type in %s) " \
#            "ORDER BY l.id) res ON (inv.move_id=res.move_id)", (partner.id, ('receivable', 'payable'))) 
#
#        res = self.cr.dictfetchall()
#        sum = 0.0
#        for r in res:
#            sum += r['debit'] - r['credit']
#            date = datetime.strptime(r['date'], report_sxw.DT_FORMAT)
#            r['progress'] = (sum>0.01 or sum<-0.01) and sum or 0.0
#            r['date'] = date.strftime('%d/%m/%Y')
#            full_moves.append(r)
#
#        self._totals(partner)
#
#        return full_moves

    def get_moves(self, partner):
        receipts = []
        full_moves = []
        write_off = []

        debit = 0.0
        credit = 0.0
        sum_writeoff = 0.0

        rec_obj = self.pool.get('payment.recibos')
        ids = rec_obj.search(self.cr, self.uid, [('partner_id', '=', partner.id), ('state', '=', 'done')])

        #print 'Recibos: '
        for r in rec_obj.browse(self.cr, self.uid, ids):
            #print 'Recibo: ', r.reference, 'Date: ', r.date_done, 'Total: ', r.totalformaspago, 'Saldo a favor: ', r.saldofavor
            receipts.append({'name': 'Rec. %s' % r.reference, 'date': r.date_done, 'debit': 0.0, 'credit': r.totalformaspago})
            credit = credit + r.total

        ml_obj = self.pool.get('account.move.line')
        inv_obj = self.pool.get('account.invoice')
        ids = inv_obj.search(self.cr, self.uid, [('partner_id', '=', partner.id), ('state', 'not in', ['draft', 'cancel'])])

        #print 'Invoices: '
        woml_ids = []
        for i in inv_obj.browse(self.cr, self.uid, ids):
            #print '\nInvoice: ', i.number, 'Date: ', i.date_invoice, 'Total: ', i.amount_total
            debit = debit + i.amount_total

            if i.documento == 'factura':
                name = 'FAC %s' % i.number
                inv_credit = 0.0
                inv_debit = i.amount_total
            elif i.documento == 'nota_credito':
                name = 'NC %s' % i.number
                inv_credit = i.amount_total
                inv_debit = 0.0
            if i.documento == 'nota_debito':
                name = 'ND %s' % i.number
                inv_credit = 0.0
                inv_debit = i.amount_total

            receipts.append({'name': name, 'date': i.date_invoice, 'debit': inv_debit, 'credit': inv_credit})

            # Pedimos las lineas de asientos que tengan ese move_id y que esten conciliados
            ml_ids = ml_obj.search(self.cr, self.uid, [('move_id', '=', i.move_id.id), ('reconcile_id', '!=', False)])

            for ml in ml_obj.browse(self.cr, self.uid, ml_ids):
                #print 'Reconcile: ', ml.reconcile_id.name, i.id, ml.invoice.id, ml.invoice.number
                reconciled_ids = ml_obj.search(self.cr, self.uid, ['|', ('name', '=', 'Write-Off'), 
                                                                        ('name', '=', 'Currency Profit/Loss'), 
                                                                        ('account_id', '=', ml.account_id.id),
                                                                        ('reconcile_id', '=', ml.reconcile_id.id)])

                # Esto de chequear si el id esta es medio una chanchada, deberiamos
                # pensarlo de otra manera.
                for woml in ml_obj.browse(self.cr, self.uid, reconciled_ids):
                    #print woml.id, woml.name, woml.debit, woml.credit
                    if woml.id not in woml_ids:
                        woml_ids.append(woml.id)
                        sum_writeoff += (woml.debit - woml.credit)

        # Las ordenamos por fecha
        receipt_ordered = sorted(receipts, key=itemgetter('date'))

        sum = 0.0
        for l in receipt_ordered:
            sum += l['debit'] - l['credit']
            date = datetime.strptime(l['date'], report_sxw.DT_FORMAT)
            l['progress'] = '%.02f' % ((sum>0.01 or sum<-0.01) and sum or 0.0)
            l['date'] = date.strftime('%d/%m/%Y')
            l['debit'] = '%.02f' % l['debit']
            l['credit'] = '%.02f' % l['credit']
            full_moves.append(l)
            #print l

        if sum_writeoff:
            debit = 0.0
            credit = 0.0
            sum += sum_writeoff
            if sum_writeoff < 0:
                credit = abs(sum_writeoff)
            else:
                debit = sum_writeoff

            progress = '%.02f' % ((sum>0.01 or sum<-0.01) and sum or 0.0)
            full_moves.append({'name': 'Diferencia por redondeo', 'date': '', 'debit': debit, 'credit': credit, 'progress': progress})

            #print 'Sum Write-Off: ', sum_writeoff

        self._totals(partner)

        return full_moves

    def _totals(self, partner):
        """Hace consulta de totales"""
        # SQL Query para totales

        self.cr.execute("SELECT count(l.id), sum(l.debit) as sum_debit, sum(l.credit) as sum_credit, sum(l.debit)-sum(l.credit) as sum_saldo " \
                        "FROM account_move_line l, account_journal j " \
                        "WHERE l.journal_id=j.id AND l.partner_id=%s " \
                        "AND l.account_id IN (select id from account_account where type in %s)", (partner.id, ('receivable', 'payable'))) 

        res = self.cr.dictfetchall()
        self.total_debit = res[0]['sum_debit']
        self.total_credit = res[0]['sum_credit']
        self.total_saldo = res[0]['sum_saldo']

    def get_total_debit(self):
        return self.total_debit

    def get_total_credit(self):
        return self.total_credit

    def get_total_saldo(self):
        return self.total_saldo

    def hello_world(self, name):
        return "Hello, %s!" % name
