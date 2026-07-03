// AG Grid module registration. Imported (for its side effect) only by the
// components that render grids, so AG Grid stays out of the entry bundle.
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

ModuleRegistry.registerModules([AllCommunityModule]);
