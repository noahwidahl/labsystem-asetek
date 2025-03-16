from app.models.container import Container
from app.utils.db import DatabaseManager

class ContainerService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_containers(self):
        print("DEBUG: Henter containere...")
        query = """
            SELECT 
                c.ContainerID,
                c.Description,
                c.ContainerTypeID,
                c.IsMixed,
                c.ContainerCapacity,
                'Aktiv' as Status
            FROM container c  /* Bemærk lowercase 'container' her */
            ORDER BY c.ContainerID DESC
        """
        
        result, _ = self.db.execute_query(query)
        print(f"DEBUG: Container-forespørgsel returnerede {len(result)} rækker")
        
        containers = []
        for row in result:
            container = Container.from_db_row(row)
            
            # Hent ekstra information
            container_with_info = self._add_container_info(container)
            containers.append(container_with_info)
        
        return containers
    
    def _add_container_info(self, container):
        # Tilføj type navn
        if container.container_type_id:
            query = "SELECT TypeName FROM ContainerType WHERE ContainerTypeID = %s"
            result, _ = self.db.execute_query(query, (container.container_type_id,))
            if result and len(result) > 0:
                container.type_name = result[0][0]
        else:
            container.type_name = 'Standard'
        
        # Tæl antal prøver
        query = """
            SELECT COUNT(ContainerSampleID) as SampleCount, SUM(Amount) as TotalItems 
            FROM ContainerSample 
            WHERE ContainerID = %s
        """
        result, _ = self.db.execute_query(query, (container.id,))
        
        if result and len(result) > 0:
            container.sample_count = result[0][0] or 0
            container.total_items = result[0][1] or 0
        else:
            container.sample_count = 0
            container.total_items = 0
        
        return container
    
    def create_container(self, container_data, user_id):
        with self.db.transaction() as cursor:
            container = Container.from_dict(container_data)
            
            if container.container_type_id:
                cursor.execute("""
                    INSERT INTO container (
                        Description, 
                        ContainerTypeID,
                        IsMixed,
                        ContainerCapacity
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    container.description,
                    container.container_type_id,
                    1 if container.is_mixed else 0,
                    container.capacity
                ))
            else:
                cursor.execute("""
                    INSERT INTO container (
                        Description,
                        IsMixed,
                        ContainerCapacity
                    )
                    VALUES (%s, %s, %s)
                """, (
                    container.description,
                    1 if container.is_mixed else 0,
                    container.capacity
                ))
            
            container_id = cursor.lastrowid
            print(f"DEBUG: Container oprettet med ID: {container_id}")
            
            # Log aktiviteten
            cursor.execute("""
                INSERT INTO History (
                    Timestamp, 
                    ActionType, 
                    UserID, 
                    Notes
                )
                VALUES (NOW(), %s, %s, %s)
            """, (
                'Container oprettet',
                user_id,
                f"Container {container_id} oprettet: {container.description}"
            ))
            
            return {
                'success': True,
                'container_id': container_id
            }