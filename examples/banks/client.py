#
#    Bank client.
#
#    The client searches the two banks and performs a set of operations.
#    (the banks are searched simply by listing a namespace prefix path)
#

import sys
import Pyro
from banks import BankError

# A bank client.
class client(object):
    def __init__(self,name):
        self.name=name
    def doBusiness(self, bank):
        print
        print '***',self.name,'is doing business with',bank.name(),':'

        print 'Creating account'
        try:
            bank.createAccount(self.name)
        except BankError,x:
            print 'Failed:',x
            print 'Removing account and trying again'
            bank.deleteAccount(self.name)
            bank.createAccount(self.name)

        print 'Deposit money'
        bank.deposit(self.name, 200.00)
        print 'Deposit money'
        bank.deposit(self.name, 500.75)
        print 'Balance=', bank.balance(self.name)
        print 'Withdraw money'
        bank.withdraw(self.name, 400.00)
        print 'Withdraw money (red)'
        try:
            bank.withdraw(self.name, 400.00)
        except BankError,x:
            print 'Failed:',x
        print 'End balance=', bank.balance(self.name)

        print 'Withdraw money from non-existing account'
        try:
            bank.withdraw('GOD',2222.22)
            print '!!! Succeeded?!? That is an error'
        except BankError,x:
            print 'Failed, as expected:',x

        print 'Deleting non-existing account'
        try:
            bank.deleteAccount('GOD')
            print '!!! Succeeded?!? That is an error'
        except BankError,x:
            print 'Failed, as expected:',x


ns=Pyro.naming.locateNS()

# list the available banks by looking in the NS for the given prefix path
banknames=[name for name in ns.list(prefix="example.banks.")]
if not banknames:
    raise RuntimeError('There are no banks to do business with!')

banks=[]    # list of banks (proxies)
print
for name in banknames:
    print "Contacting bank: ",name
    uri=ns.lookup(name)
    banks.append(Pyro.core.Proxy(uri))

# Different clients that do business with all banks
irmen = client('Irmen')
suzy = client('Suzy')

for bank in banks:
    irmen.doBusiness(bank)
    suzy.doBusiness(bank)

# List all accounts
print
for bank in banks:
    print 'The accounts in the',bank.name(),':'
    accounts = bank.allAccounts()
    for name in accounts.keys():
        print '  ',name,':',accounts[name]
