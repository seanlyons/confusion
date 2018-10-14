-- canonical source of tags. Id is PKID; `name` is unique.
CREATE TABLE IF NOT EXISTS tags (
    id integer PRIMARY KEY,
    name text not null,
    namespace text not null,
    added_by text not null,
    added_ts BIG INT not null,
    changed_ts big int,
    disabled SMALL INT DEFAULT 0,
    UNIQUE(name)
);

-- a list of all input for all combos. Select by (tag1id, tag2id, namespace), which are non-unique, even in combination.
CREATE TABLE IF NOT EXISTS combos (
    id integer PRIMARY KEY,
    tag1id BIG INT not null,
    tag2id BIG INT not null,
    namespace text not null,
    username text not null,
    description text not null,
    added_ts BIG INT,
    changed_ts big int,
    disabled SMALL INT DEFAULT 0
);

-- allow multiple namespaces to exist in the same install, for different contexts/permission sets.
CREATE TABLE IF NOT EXISTS namespaces (
    id integer PRIMARY KEY,
    name text not null,
    owner_ids text not null, --comma-separated list containing the ids of all users eligible to administer this namespace
    permissions text not null, --comma-separated list of different permissions. Use to determine who can view/add to this namespace.
    description text,
    added_ts BIG INT,
    changed_ts big int,
    disabled SMALL INT DEFAULT 0,
    UNIQUE(name)
);

-- all users
CREATE TABLE IF NOT EXISTS users (
    id integer PRIMARY KEY,
    email text not null,
    password_hash text not null,
    password_hash_method text not null,
    changed_ts big int,
    permissions text default null,   --comma-separated list of all special permissions this user possesses
    namespaces text default null,    --comma-separated list containing the IDs of all namespaces this user can access.
    UNIQUE(email)
);
