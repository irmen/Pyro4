#
#    Bank client.
#
#    The client searches the two banks and performs a set of operations.
#    (the banks are searched simply by listing a namespace prefix path)
#

from __future__ import print_function
import Pyro4.naming


# A bank client.
class client(object):
    def __init__(self, name):
        self.name = name

    def doBusiness(self, bank):
        print("\n*** %s is doing business with %s:" % (self.name, bank.name()))
        print("Creating account")
        try:
            bank.createAccount(self.name)
        except ValueError as x:
            print("Failed: %s" % x)
            print("Removing account and trying again")
            bank.deleteAccount(self.name)
            bank.createAccount(self.name)

        print("Deposit money")
        bank.deposit(self.name, 200.00)
        print("Deposit money")
        bank.deposit(self.name, 500.75)
        print("Balance=%.2f" % bank.balance(self.name))
        print("Withdraw money")
        bank.withdraw(self.name, 400.00)
        print("Withdraw money (overdraw)")
        try:
            bank.withdraw(self.name, 400.00)
        except ValueError as x:
            print("Failed: %s" % x)
        print("End balance=%.2f" % bank.balance(self.name))

        print("Withdraw money from non-existing account")
        try:
            bank.withdraw('GOD', 2222.22)
            print("!!! Succeeded?!? That is an error")
        except KeyError as x:
            print("Failed as expected: %s" % x)

        print("Deleting non-existing account")
        try:
            bank.deleteAccount('GOD')
            print("!!! Succeeded?!? That is an error")
        except KeyError as x:
            print("Failed as expected: %s" % x)


ns = Pyro4.naming.locateNS()

# list the available banks by looking in the NS for the given prefix path
banknames = [name for name in ns.list(prefix="example.banks.")]
if not banknames:
    raise RuntimeError('There are no banks to do business with!')

banks = []  # list of banks (proxies)
print()
for name in banknames:
    print("Contacting bank: %s" % name)
    uri = ns.lookup(name)
    banks.append(Pyro4.core.Proxy(uri))

# Different clients that do business with all banks
irmen = client('Irmen')
suzy = client('Suzy')

for bank in banks:
    irmen.doBusiness(bank)
    suzy.doBusiness(bank)

# List all accounts
print()
for bank in banks:
    print("The accounts in the %s:" % bank.name())
    accounts = bank.allAccounts()
    for name in accounts.keys():
        print("  %s : %.2f" % (name, accounts[name]))
