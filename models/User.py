class User:
    def __init__(self, uid, fullname, email) -> None:
        self.uid = uid
        self.fullname = fullname
        self.email = email

    def to_dict(self):
        return {
            'id': self.uid,
            'fullname': self.fullname,
            'email' : self.email
            # Add other fields you want to include
        }