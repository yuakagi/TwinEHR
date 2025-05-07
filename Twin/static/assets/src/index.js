// <-- begin: Node modules -->

// Import JQuery
import $ from 'jquery';
// Import select2 
import 'select2';
import 'select2/dist/css/select2.min.css';
// Import Bootstrap CSS
import 'bootstrap/dist/css/bootstrap.min.css';
// Import Bootstrap Icons CSS
import 'bootstrap-icons/font/bootstrap-icons.css';
// Import Day.js
import dayjs from 'dayjs';
// Import Font CSS
import '@fontsource/inter';
// Import Bootstrap JS (No need for import 'bootstrap/dist/js/bootstrap.bundle.min.js';)
import * as bootstrap from 'bootstrap';
window.bootstrap = bootstrap;
// Import Chart.js
import Chart from 'chart.js/auto';
// Import ApexCharts
import ApexCharts from 'apexcharts';
// Import Typed.js
import Typed from 'typed.js';
// Import DataTables.net Bootstrap 5 styling
import 'datatables.net-bs5';
// Import SweetAlert2
import Swal from 'sweetalert2';
// Import flatpickr
import flatpickr from "flatpickr";
import "flatpickr/dist/flatpickr.min.css";
// Import fireworks-js
import {
    Fireworks
} from 'fireworks-js';
// <-- end: Node modules -->

// <-- begin: Custom modules -->

// Import custom CSS (This must come last, to override other styles)
import './css/custom.css';
import './css/timeline.css';

// <-- begin: Global exports -->
window.$ = $;
window.jQuery = $;
window.dayjs = dayjs;
window.Typed = Typed;
window.Chart = Chart;
window.ApexCharts = ApexCharts;
window.Swal = Swal;
window.flatpickr = flatpickr;
window.Fireworks = Fireworks;
// <-- end: Global exports -->