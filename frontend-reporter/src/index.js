import React from 'react';
import ReactDOM from 'react-dom';
// import * as Sentry from '@sentry/browser';
import './index.css';
import App from './App';

// prod: intranet
// Sentry.init({dsn: 'http://0e513e677ff94916b3bae55a6aff2974@10.1.1.181:9000/2', transport});
// dev: openvpn
// Sentry.init({dsn: 'http://1ed6c4141d2d428399c6c5971cfe741b:803d763ad5af4f2bab49d46bb65d93a3@2.0.205.117:9000/8'});

ReactDOM.render(<App />, document.getElementById('root'));
