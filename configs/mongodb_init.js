db.createUser(
    {
        user: "user",
        pwd: "user_pwd",
        roles: [
            {
                role: "readWrite",
                db: "defaultdb"
            }
        ]
    }
);