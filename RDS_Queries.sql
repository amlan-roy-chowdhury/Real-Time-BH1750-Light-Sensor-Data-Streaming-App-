-- Get all records--

SELECT * FROM lux_file_summary;


-- View the entire table by order of descending file_data--

SELECT * FROM lux_file_summary ORDER BY file_date DESC LIMIT 10;


-- Get file counts per day --

SELECT file_date, COUNT(*) 
FROM lux_file_summary
GROUP BY file_date
ORDER BY file_date DESC;


-- Check average lux overtime --

SELECT file_date, AVG(avg_lux) 
FROM lux_file_summary
GROUP BY file_date
ORDER BY file_date;

-- View daily trends --

SELECT file_date, COUNT(*) AS files, AVG(avg_lux) AS avg_lux_day
FROM lux_file_summary
GROUP BY file_date
ORDER BY file_date DESC;


-- Delete duplicate test runs --

DELETE FROM lux_file_summary
WHERE id NOT IN (
    SELECT MIN(id)
    FROM lux_file_summary
    GROUP BY filename
);
