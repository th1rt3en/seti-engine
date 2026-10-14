-- Accounts are a username and a password (decision D29): no email. A registered username is unique, whatever its case.
-- (Guests may share names; the website refuses a guest name that a registered user has.) The email column of 0001 stays and is not used.
CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(lower(name)) WHERE is_guest = 0;
