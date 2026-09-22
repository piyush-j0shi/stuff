" --- Basic Settings ---
set nocompatible
call plug#begin('~/.vim/plugged')
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

set mouse=a
set ttymouse=sgr
let g:rustfmt_autosave = 0
function! s:RustEdition() abort
  let l:manifest = findfile('Cargo.toml', expand('%:p:h') . ';')
  if l:manifest !=# ''
    for l:line in readfile(l:manifest, '', 40)
      let l:m = matchlist(l:line, '^\s*edition\s*=\s*"\(\d\+\)"')
      if !empty(l:m) | return l:m[1] | endif
    endfor
  endif
  return '2024'
endfunction
function! s:RustFmtOnSave() abort
  if !executable('rustfmt') | return | endif
  let l:view = winsaveview()
  let l:tmp = tempname() . '.rs'
  call writefile(getline(1, '$'), l:tmp)
  call system(printf('rustfmt --edition %s %s',
        \ s:RustEdition(), shellescape(l:tmp)))
  if v:shell_error == 0
    let l:new = readfile(l:tmp)
    if l:new !=# getline(1, '$')
      silent! keepjumps %delete _
      call setline(1, l:new)
    endif
  else
    echohl WarningMsg | echo 'rustfmt failed - file saved unformatted' | echohl None
  endif
  call delete(l:tmp)
  call winrestview(l:view)
endfunction
augroup RustFmtOnSave
  autocmd!
  autocmd BufWritePre *.rs call s:RustFmtOnSave()
augroup END
let s:comment_map = {
      \ 'rust': '//', 'c': '//', 'cpp': '//', 'java': '//', 'javascript': '//',
      \ 'typescript': '//', 'go': '//', 'swift': '//', 'scala': '//', 'php': '//',
      \ 'python': '#', 'sh': '#', 'bash': '#', 'zsh': '#', 'ruby': '#', 'perl': '#',
      \ 'yaml': '#', 'toml': '#', 'conf': '#', 'make': '#', 'dockerfile': '#',
      \ 'gitconfig': '#', 'vim': '"', 'lua': '--', 'sql': '--', 'haskell': '--',
      \ }
function! ToggleComment() range
  let l:cs = get(s:comment_map, &filetype, '')
  if l:cs ==# ''
    echohl WarningMsg | echo 'No comment string for filetype: ' . &filetype | echohl None
    return
  endif
  let l:pat = '^\s*' . escape(l:cs, '\/*.~&')
  let l:commented = 1
  for l:n in range(a:firstline, a:lastline)
    let l:line = getline(l:n)
    if l:line =~# '^\s*$' | continue | endif
    if l:line !~# l:pat
      let l:commented = 0
      break
    endif
  endfor
  for l:n in range(a:firstline, a:lastline)
    let l:line = getline(l:n)
    if l:line =~# '^\s*$' | continue | endif
    if l:commented
      call setline(l:n, substitute(l:line,
            \ '^\(\s*\)' . escape(l:cs, '\/*.~&') . '\s\?', '\1', ''))
    else
      call setline(l:n, substitute(l:line, '^\(\s*\)',
            \ '\1' . escape(l:cs, '\&~') . ' ', ''))
    endif
  endfor
endfunction
nnoremap <silent> cc :<C-u>execute '.,.+' . (v:count1 - 1) . 'call ToggleComment()'<CR>
vnoremap <silent> cc :call ToggleComment()<CR>gv
vnoremap <silent> gc :call ToggleComment()<CR>gv
set cursorline
set ruler
set scrolloff=5
set hlsearch
set incsearch
set wrapscan
set ignorecase
set smartcase
set magic
set maxmempattern=1000
augroup numbertoggle
  autocmd!
  autocmd BufEnter,FocusGained,InsertLeave * set relativenumber
  autocmd BufLeave,FocusLost,InsertEnter   * set norelativenumber
augroup END
nnoremap <F3> :vert terminal<CR>
nnoremap <Space> /
nnoremap <Leader><Space> ?
nnoremap <Leader>m :noh<CR>
nnoremap n nzz
nnoremap N Nzz
function! s:VSetSearch() abort
  let l:tmp = @s
  normal! gv"sy
  let @/ = '\V' . substitute(escape(@s, '/\'), '\n', '\\n', 'g')
  let @s = l:tmp
endfunction
nnoremap <silent> <Leader><CR> :let @/='\<<C-R>=expand("<cword>")<CR>\>'<CR>:set hlsearch<CR>
vnoremap <silent> <Leader><CR> :<C-U>call <SID>VSetSearch()<CR>:set hlsearch<CR>
