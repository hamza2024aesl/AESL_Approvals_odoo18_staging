def uninstall_hook(cr, registry):
    cr.execute(
        """
        delete from ir_model where model like 'x_bve.%'
    """
    )
    cr.execute(
        """
        delete from bve_view where model_name like 'x_bve.%'
    """
    )
    cr.execute(
        """
        SELECT 'DROP VIEW ' || table_name
          FROM information_schema.views
         WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
           AND table_name like 'x_bve_%'
    """
    )
    results = list(cr.fetchall())
    for result in results:
        cr.execute(result[0])
