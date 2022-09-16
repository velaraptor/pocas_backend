"""Create Database for User Logins"""
# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, E0611

from main import db


def main():
    """Create User database"""
    db.create_all()


if __name__ == "__main__":
    main()
