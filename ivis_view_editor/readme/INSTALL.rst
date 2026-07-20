In the Odoo configuration file add ``ivis_view_editor`` in the list
``server_wide_modules``:

.. code-block:: ini

  [options]
  (...)
  server_wide_modules = web,ivis_view_editor
  (...)

Alternatively specify ``--load=ivis_view_editor`` when starting Odoo by command line.

Optionally it is possible to enable the view of the ER Diagram. For this you
need to install `Graphviz`, an open source graph visualization software:

.. code-block:: bash

   ``sudo apt-get install graphviz``
