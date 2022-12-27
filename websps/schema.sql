DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS nucleus;
DROP TABLE IF EXISTS reaction;
DROP TABLE IF EXISTS target_material;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE nucleus (
    id INTEGER PRIMARY KEY,
    z INTEGER NOT NULL,
    a INTEGER NOT NULL,
    mass FLOAT NOT NULL,
    element TEXT NOT NULL,
    isotope TEXT NOT NULL
);


CREATE TABLE target_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mat_name TEXT NOT NULL,
    mat_symbol TEXT NOT NULL,
    compounds TEXT NOT NULL,
    thicknesses TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE reaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_mat_id INTEGER NOT NULL,
    rxn_symbol TEXT NOT NULL,
    latex_rxn_symbol TEXT NOT NULL,
    target_nuc_id INTEGER NOT NULL,
    projectile_nuc_id INTEGER NOT NULL,
    ejectile_nuc_id INTEGER NOT NULL,
    residual_nuc_id INTEGER NOT NULL,
    excitations TEXT,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (target_mat_id) REFERENCES target_material (id),
    FOREIGN KEY (target_nuc_id) REFERENCES nucleus (id),
    FOREIGN KEY (projectile_nuc_id) REFERENCES nucleus (id),
    FOREIGN KEY (ejectile_nuc_id) REFERENCES nucleus (id),
    FOREIGN KEY (residual_nuc_id) REFERENCES nucleus (id)
);