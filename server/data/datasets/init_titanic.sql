CREATE TABLE titanic (
    Survived BOOLEAN,
    Pclass INT,
    Name TEXT,
    Sex TEXT,
    Age DOUBLE PRECISION,
    SibSp INT,
    Parch INT,
    Fare DOUBLE PRECISION
);
 
COPY titanic
FROM '/docker-entrypoint-initdb.d/titanic.csv'
DELIMITER ','
CSV HEADER;