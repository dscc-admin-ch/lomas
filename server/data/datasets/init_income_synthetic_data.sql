CREATE TABLE income_synthetic_data (
    region INT,
    eco_branch INT,
    profession INT,
    education INT,
    age INT,
    sex INT,
    income DOUBLE PRECISION
);
 
COPY income_synthetic_data
FROM '/docker-entrypoint-initdb.d/income_synthetic_data.csv'
DELIMITER ','
CSV HEADER;