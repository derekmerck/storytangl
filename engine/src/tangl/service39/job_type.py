from enum import Enum, auto

class JobType(Enum):
    CREATE = auto()
    READ = auto()
    UPDATE = auto()
    DELETE = auto()

    def req_writeback(self):
        return self in [self.CREATE, self.UPDATE, self.DELETE]

