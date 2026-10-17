import {createHandler} from './handler.ts';
Deno.serve(createHandler(key=>Deno.env.get(key)));
