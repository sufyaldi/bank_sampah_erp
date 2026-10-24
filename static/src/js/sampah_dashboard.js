/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class SampahDashboard extends Component {
    static template = "sirita_sampah.SampahDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.menuService = useService("menu");

        this.state = proxy({
            statistics: {
                total_nasabah: 0,
                total_weight: 0,
                total_points: 0,
                monthly_tx_count: 0,
                monthly_weight: 0,
                active_pickups: 0,
                pending_withdrawals: 0,
                categories_data: [],
            },
            loading: true,
            sidebarCollapsed: false,
            activeMenu: "monitoring",
            showAppDrawer: false,
            appSearchTerm: "",
            expandedParents: {
                operasional: true,
                keanggotaan: false,
                master: false,
            },
        });

        onWillStart(async () => {
            await this.loadStatistics();
        });

        onMounted(() => {
            document.body.classList.add("sampah_dashboard");
        });

        onWillUnmount(() => {
            document.body.classList.remove("sampah_dashboard");
        });
    }

    async loadStatistics() {
        try {
            this.state.loading = true;
            const res = await this.orm.call("sampah.dashboard", "get_statistics", []);
            if (res) {
                this.state.statistics = res;
            }
        } catch (e) {
            console.error("Error loading sampah dashboard stats:", e);
        } finally {
            this.state.loading = false;
        }
    }

    toggleSidebar() {
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
    }

    toggleParent(key) {
        if (this.state.expandedParents[key] === undefined) {
            this.state.expandedParents[key] = false;
        }
        this.state.expandedParents[key] = !this.state.expandedParents[key];
    }

    onNavigateMenu(menuKey, actionXmlId) {
        this.state.activeMenu = menuKey;
        if (actionXmlId) {
            this.openAction(actionXmlId);
        }
    }

    async openAction(actionXmlId) {
        try {
            const fullXmlId = actionXmlId.includes(".") ? actionXmlId : `sirita_sampah.${actionXmlId}`;
            await this.actionService.doAction(fullXmlId);
        } catch (e) {
            console.error(`Error opening action ${actionXmlId}:`, e);
        }
    }

    // App Drawer Methods
    onOpenAppDrawer() {
        this.state.showAppDrawer = true;
        this.state.appSearchTerm = "";
    }

    onCloseAppDrawer() {
        this.state.showAppDrawer = false;
        this.state.appSearchTerm = "";
    }

    onAppSearchInput(ev) {
        this.state.appSearchTerm = ev.target.value.toLowerCase();
    }

    getAppsList() {
        try {
            const apps = this.menuService.getApps() || [];
            if (!this.state.appSearchTerm) {
                return apps;
            }
            return apps.filter(app => (app.name || "").toLowerCase().includes(this.state.appSearchTerm));
        } catch (e) {
            return [];
        }
    }

    async onSelectApp(app) {
        this.onCloseAppDrawer();
        if (app) {
            await this.menuService.selectMenu(app);
        }
    }
}

SampahDashboard.template = "sirita_sampah.SampahDashboard";

registry.category("actions").add("sirita_sampah.dashboard", SampahDashboard);
