
# the bank uses this exception to say there's something wrong:
class BankError(Exception):
    pass

# Unrestricted account.
class Account(object):
    def __init__(s):
        s._balance=0.0
    def withdraw(s, amount):
        s._balance-=amount
    def deposit(s,amount):
        s._balance+=amount
    def balance(s):
        return s._balance

# Restricted withdrawal account.
class RestrictedAccount(Account):
    def withdraw(s, amount):
        if amount<=s._balance:
            s._balance-=amount
        else:
            raise BankError('insufficent balance')

# Abstract bank.
class Bank(object):
    def __init__(s):
        s.accounts={}
    def name(s):
        pass  # must override this!
    def createAccount(s, name):
        pass  # must override this!
    def deleteAccount(s, name):
        try:
            del s.accounts[name]
        except KeyError:
            raise BankError('unknown account')
    def deposit(s, name, amount):
        try:
            return s.accounts[name].deposit(amount)
        except KeyError:
            raise BankError('unknown account')
    def withdraw(s, name, amount):
        try:
            return s.accounts[name].withdraw(amount)
        except KeyError:
            raise BankError('unknown account')
    def balance(s, name):
        try:
            return s.accounts[name].balance()
        except KeyError:
            raise BankError('unknown account')
    def allAccounts(s):
        accs = {}
        for name in s.accounts.keys():
            accs[name] = s.accounts[name].balance()
        return accs


# Special bank: Rabobank. It has unrestricted accounts.
class Rabobank(Bank):
    def name(s):
        return 'Rabobank'
    def createAccount(s,name):
        if name in s.accounts:
            raise BankError('Account already exists')
        s.accounts[name]=Account()


# Special bank: ABN. It has restricted accounts.
class ABN(Bank):
    def name(s):
        return 'ABN bank'
    def createAccount(s,name):
        if name in s.accounts:
            raise BankError('Account already exists')
        s.accounts[name]=RestrictedAccount()
