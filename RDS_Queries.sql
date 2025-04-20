-- Get all records--

SELECT * FROM lux_file_summary;


-- View the entire table by order of descending file_data--

SELECT * FROM lux_file_summary ORDER BY file_date DESC LIMIT 10;

-- View the entire table by order of descending created_at (latest files first)--

SELECT * FROM lux_file_summary ORDER BY created_at DESC LIMIT 10;


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


--Grafana Dashboard Queries--

--Today's Min Lux Recorded--
SELECT MIN(min_lux) AS min_lux
FROM lux_file_summary
WHERE file_date = (
  SELECT MAX(file_date) FROM lux_file_summary
);

--Today's Max Lux Recorded--
SELECT MIN(min_lux) AS min_lux
FROM lux_file_summary
WHERE file_date = (
  SELECT MAX(file_date) FROM lux_file_summary
);


--Total Records Today--
SELECT SUM(record_count) AS total_records
FROM lux_file_summary
WHERE file_date = (SELECT MAX(file_date) FROM lux_file_summary);


--Daily Summary Table--
SELECT 
  filename,
  TO_CHAR(created_at, 'HH24:MI:SS') AS upload_time,
  record_count,
  min_lux,
  max_lux,
  avg_lux
FROM lux_file_summary
WHERE file_date = (SELECT MAX(file_date) FROM lux_file_summary)
ORDER BY created_at DESC;

--Min Lux Over Time--

SELECT
  created_at AS time,
  min_lux
FROM lux_file_summary
ORDER BY created_at;

--Max Lux Over Time--
SELECT
  created_at AS time,
  max_lux
FROM lux_file_summary
ORDER BY created_at;

--Average Lux Over Time--
SELECT
  created_at AS time,
  avg_lux
FROM lux_file_summary
ORDER BY created_at;

--Latest Average Lux Reading--
SELECT
  created_at AS time,
  avg_lux
FROM lux_file_summary
ORDER BY created_at DESC
LIMIT 1
