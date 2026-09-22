" --- Basic Settings ---
call plug#begin('~/.vim/p₹lugged')
Plug 'sheerun/vim-polyglot'
Plug 'neoclide/coc.nvim', {'branch': 'release'}
Plug 'ctrlpvim/ctrlp.vim'
Plug 'preservim/nerdtree'
call plug#end()

set number
set relativenumber
set termguicolors

highlight Pmenu guibg=#2d3139 guifg=#cccccc ctermbg=236 ctermfg=250
highlight PmenuSel guibg=#005f87 guifg=#ffffff ctermbg=25 ctermfg=15
highlight CocFloating guibg=#2d3139 guifg=#cccccc

nmap <silent> gd <Plug>(coc-definition)
nnoremap <C-b> :NERDTreeToggle<CR>
inoremap <silent><expr> <TAB>
      \ coc#pum#visible() ? coc#pum#confirm() :
      \ CheckBackspace() ? "\<Tab>" :
      \ coc#refresh()

inoremap <expr><S-TAB> coc#pum#visible() ? coc#pum#prev(1) : "\<C-h>"
inoremap <silent><expr> <CR> "\<CR>"

function! CheckBackspace() abort
  let col = col('.') - 1
  return !col || getline('.')[col - 1]  =~# '\s'
endfunction
