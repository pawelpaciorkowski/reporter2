import { createStore /*, applyMiddleware */ } from 'redux';

const rootReducer = (state) => state;

export function configureStore(initialState) {
    // let middleware = applyMiddleware(logger);
    //
    // if (process.env.NODE_ENV !== 'production') {
    //     middleware = composeWithDevTools(middleware);
    // }

    const store = createStore(rootReducer, initialState);

    // if (module.hot) {
    //     module.hot.accept('app/reducers', () => {
    //         const nextReducer = require('app/reducers');
    //         store.replaceReducer(nextReducer);
    //     });
    // }

    return store;
}
