from .postgres import PostgresDatasource
import logging
from config import Config

# Utwórz logger
log = logging.getLogger(__name__)

class Awarie(PostgresDatasource):
    def __init__(self, read_write=False):
        cfg = Config()
        super().__init__(cfg.DATABASE_AWARIE, read_write=read_write)



    def lista_awarii(self, model_name=None, symbol=None, serial_number=None,
                 workshop_name=None, device_type=None,
                 laboratory_name=None, manufacturer=None,
                 date_from=None, date_to=None):
    
        sql = """
        SELECT 
    d.model_name AS model_name,
    d.symbol AS device_symbol,
    d.serial_number,
    dm.name AS manufacturer, 
    s.type_name AS service_type,
    s.notification_date,
    s.arrival_date,
    s.resolve_date,
    s.company_name,
    s.cost,
    s.downtime_hours,
    s.report_number,
    d.laboratory_name,
    d.workshop_name,
    d.type_name AS device_type
FROM 
    v_service_event_details s
JOIN 
    v_devices d ON s.device_id = d.id
LEFT JOIN
    device_manufacturers dm ON d.manufacturer_id = dm.id  
WHERE 
    1=1

        """
        params = []

        # Dynamiczne filtry
        if model_name:
            sql += " AND d.model_name ILIKE %s"
            params.append(f"%{model_name}%")
        if symbol:
            sql += " AND d.symbol ILIKE %s"
            params.append(f"%{symbol}%")
        if serial_number:
            sql += " AND d.serial_number ILIKE %s"
            params.append(f"%{serial_number}%")
        if manufacturer:
            sql += " AND dm.name ILIKE %s"
            params.append(f"%{manufacturer}%")
        if manufacturer:
            sql += " AND dm.name ILIKE %s"
            params.append(f"%{manufacturer}%")
        if device_type:
            sql += " AND d.type_name = %s"
            params.append(device_type)
        if laboratory_name:
            sql += " AND d.laboratory_name ILIKE %s"
            params.append(f"%{laboratory_name}%")
        if date_from:
            sql += " AND s.notification_date >= %s"
            params.append(date_from)
        if date_to:
            sql += " AND s.notification_date <= %s"
            params.append(date_to)

        sql += " ORDER BY d.model_name, s.notification_date"

        return self.select(sql, params)
