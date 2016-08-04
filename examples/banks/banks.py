import Pyro4


# Unrestricted account.
class Account(object):
    def __init__(self):
        self._balance = 0.0

    def withdraw(self, amount):
        self._balance -= amount

    def deposit(self, amount):
        self._balance += amount

    def balance(self):
        return self._balance


# Restricted withdrawal account.
class RestrictedAccount(Account):
    def withdraw(self, amount):
        if amount <= self._balance:
            self._balance -= amount
        else:
            raise ValueError('insufficent balance')


# Abstract bank.
@Pyro4.expose
class Bank(object):
    def __init__(self):
        self.accounts = {}

    def name(self):
        pass  # must override this!

    def createAccount(self, name):
        pass  # must override this!

    def deleteAccount(self, name):
        try:
            del self.accounts[name]
        except KeyError:
            raise KeyError('unknown account')

    def deposit(self, name, amount):
        try:
            return self.accounts[name].deposit(amount)
        except KeyError:
            raise KeyError('unknown account')

    def withdraw(self, name, amount):
        try:
            return self.accounts[name].withdraw(amount)
        except KeyError:
            raise KeyError('unknown account')

    def balance(self, name):
        try:
            return self.accounts[name].balance()
        except KeyError:
            raise KeyError('unknown account')

    def allAccounts(self):
        accs = {}
        for name in self.accounts.keys():
            accs[name] = self.accounts[name].balance()
        return accs


# Special bank: Rabobank. It has unrestricted accounts.
@Pyro4.expose
class Rabobank(Bank):
    def name(self):
        return 'Rabobank'

    def createAccount(self, name):
        if name in self.accounts:
            raise ValueError('Account already exists')
        self.accounts[name] = Account()


# Special bank: ABN. It has restricted accounts.
@Pyro4.expose
class ABN(Bank):
    def name(self):
        return 'ABN bank'

    def createAccount(self, name):
        if name in self.accounts:
            raise ValueError('Account already exists')
        self.accounts[name] = RestrictedAccount()
