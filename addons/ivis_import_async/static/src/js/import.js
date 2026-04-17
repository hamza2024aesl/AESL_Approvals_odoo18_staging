/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { BaseImportModel } from "@base_import/import_model";
import { ImportAction } from "@base_import/import_action/import_action";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

let use_queue_check = false;


patch(BaseImportModel.prototype, {
    async init() {
        await super.init(...arguments);
        console.log("BASE import", this)
        this.importOptionsValues.use_queue = {
            value: false,
        };
        use_queue_check = false;
    },
});



patch(ImportAction.prototype, {

    async onOptionChanged(name, value, fieldName = null) {
        super.onOptionChanged(...arguments);
        console.log("NAME", name, value)
        use_queue_check = value
        },

    async setup() {
            await super.setup(...arguments);
            this.use_queue = false;
    },

    async handleImport(isTest = true) {
        if (use_queue_check)
        {
            const delayPromise = new Promise(resolve => setTimeout(resolve, 1000));
            delayPromise.then(async () => {
                const message = isTest ? _t("Testing") : _t("Importing");
                let res = { ids: [] };
                try {
                    const data = this.model.executeImport(
                        isTest,
                        this.totalSteps,
                        this.state.importProgress
                    );
                    this.notification.add(_t("Import process is running in the background."), {
                        type: "success",
                    });
                    this.env.config.historyBack();
                    this.model.unblock();
                }
                finally {
                    this.model.unblock();
                }
            });
        }
        else
            {
               super.handleImport(...arguments);
            }
    }
});
