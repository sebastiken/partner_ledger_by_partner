##############################################################################
#
# Copyright (c) 2008-2010 SIA "KN dati". (http://kndati.lv) All Rights Reserved.
#                    General contacts <info@kndati.lv>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from report import report_sxw
from report.report_sxw import rml_parse
import lorem
import random
from datetime import datetime

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
        print 'Data: ', data
        print 'Objects: ', objects
        print 'Ids: ', ids
        super(Parser, self).set_context(objects, data, ids, report_type)

    def get_moves(self, partner):
        full_moves = []

        # SQL Query que nos entrega toda la informacion incluido
        # informacion del objeto account_invoice
        self.cr.execute("SELECT res.*, res.ref, inv.id, inv.number from account_invoice inv RIGHT JOIN " \
        "(SELECT l.id, l.move_id, l.date,j.code, l.ref as ref, l.name, l.debit, l.credit " \
            "FROM account_move_line l " \
            "LEFT JOIN account_journal j " \
            "ON (l.journal_id = j.id) " \
            "WHERE l.partner_id = %s " \
            "AND l.account_id IN (select id from account_account where type in %s) " \
            "ORDER BY l.id) res ON (inv.move_id=res.move_id)", (partner.id, ('receivable', 'payable'))) 

        res = self.cr.dictfetchall()
        sum = 0.0
        for r in res:
            sum += r['debit'] - r['credit']
            date = datetime.strptime(r['date'], report_sxw.DT_FORMAT)
            r['progress'] = (sum>0.01 or sum<-0.01) and sum or 0.0
            r['date'] = date.strftime('%d/%m/%Y')
            full_moves.append(r)

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
